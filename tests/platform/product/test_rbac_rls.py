"""RLS/RBAC tests for every role/action pair in phase-02's Authorization Model.

Runs against a real (ephemeral, native) Postgres server with the actual
platform .igrations applied — no mocked database.
"""

from __future__ import annotations

import json

from psycopg import Rollback, sql

from .conftest import (
    ANALYST_ID,
    OTHER_ANALYST_ID,
    PLATFORM_ADMIN_ID,
    PLATFORM_OPERATOR_ID,
    PLATFORM_VIEWER_ID,
    REPO_ROOT,
    run_as,
)


def test_analyst_can_save_own_report(seeded_db):
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "insert into saved_reports (owner_id, company_id, payload) "
        "values (%s, 'ACME', '{}'::jsonb)",
        (ANALYST_ID,),
    )
    assert result["error"] is None


def test_analyst_cannot_save_report_for_another_user(seeded_db):
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "insert into saved_reports (owner_id, company_id, payload) "
        "values (%s, 'ACME', '{}'::jsonb)",
        (OTHER_ANALYST_ID,),
    )
    assert result["error"] is not None


def test_analyst_cannot_read_evidence_session(seeded_db):
    result = run_as(seeded_db, ANALYST_ID, "aal1", "select * from evidence_session")
    assert result["rows"] == []


def test_platform_viewer_with_aal2_can_read_evidence_session(seeded_db):
    result = run_as(seeded_db, PLATFORM_VIEWER_ID, "aal2", "select * from evidence_session")
    assert result["error"] is None
    assert result["rows"] == []


def test_platform_viewer_without_aal2_cannot_read_evidence_session(seeded_db):
    result = run_as(seeded_db, PLATFORM_VIEWER_ID, "aal1", "select * from evidence_session")
    assert result["rows"] == []


def test_platform_viewer_cannot_provision(seeded_db):
    result = run_as(
        seeded_db,
        PLATFORM_VIEWER_ID,
        "aal2",
        "select * from create_evidence_session('viewer', 'idem-1')",
    )
    assert result["error"] is not None


def test_platform_operator_with_aal2_can_provision(seeded_db):
    result = run_as(
        seeded_db,
        PLATFORM_OPERATOR_ID,
        "aal2",
        "select * from create_evidence_session('operator', 'idem-2')",
    )
    assert result["error"] is None


def test_direct_insert_into_evidence_session_denied_even_for_operator(seeded_db):
    """create_evidence_session() is the only creation path; a raw client
    INSERT must be denied regardless of role, since there is no INSERT policy
    on evidence_session at all."""
    result = run_as(
        seeded_db,
        PLATFORM_OPERATOR_ID,
        "aal2",
        "insert into evidence_session (actor, idempotency_key) values ('operator', 'idem-direct')",
    )
    assert result["error"] is not None


def test_direct_update_of_evidence_session_denied_even_for_operator(seeded_db):
    """request_session_transition() is the only mutation path; a raw client
    UPDATE (bypassing the fencing token / outbox / audit trail entirely) must
    be denied regardless of role."""
    seeded_db.execute(
        "insert into evidence_session (actor, idempotency_key) values ('seed', 'idem-direct-2')"
    )
    session_id = seeded_db.execute(
        "select id from evidence_session order by created_at desc limit 1"
    ).fetchone()[0]

    result = run_as(
        seeded_db,
        PLATFORM_OPERATOR_ID,
        "aal2",
        "update evidence_session set state = 'READY', fencing_token = 'pwned' "
        "where id = %s returning state",
        (session_id,),
    )
    # UPDATE privilege on evidence_session is revoked outright (not merely
    # RLS-filtered), so this raises a permission error rather than matching
    # zero rows.
    assert result["error"] is not None

    state = seeded_db.execute(
        "select state from evidence_session where id = %s", (session_id,)
    ).fetchone()[0]
    assert state == "OFF"


def test_anon_cannot_read_evidence_session(seeded_db):
    result = run_as(seeded_db, None, "aal2", "select * from evidence_session", pg_role="anon")
    assert result["error"] is not None or result["rows"] == []


def test_platform_operator_cannot_manage_roles(seeded_db):
    result = run_as(
        seeded_db,
        PLATFORM_OPERATOR_ID,
        "aal2",
        "update profiles set role = 'platform_admin' where user_id = %s returning role",
        (ANALYST_ID,),
    )
    assert result["rows"] == []


def test_platform_admin_with_aal2_can_manage_roles(seeded_db):
    result = run_as(
        seeded_db,
        PLATFORM_ADMIN_ID,
        "aal2",
        "update profiles set role = 'platform_viewer' where user_id = %s returning role",
        (ANALYST_ID,),
    )
    assert result["error"] is None
    assert result["rows"][0][0] == "platform_viewer"


def test_platform_admin_without_aal2_cannot_manage_roles(seeded_db):
    result = run_as(
        seeded_db,
        PLATFORM_ADMIN_ID,
        "aal1",
        "update profiles set role = 'platform_viewer' where user_id = %s returning role",
        (ANALYST_ID,),
    )
    assert result["rows"] == []


def test_request_session_transition_rejects_analyst(seeded_db):
    seeded_db.execute(
        "insert into evidence_session (actor, idempotency_key) values ('seed', 'idem-seed')"
    )
    session_id = seeded_db.execute("select id from evidence_session limit 1").fetchone()[0]
    fencing_token = seeded_db.execute(
        "select fencing_token from evidence_session where id = %s", (session_id,)
    ).fetchone()[0]

    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal2",
        "select * from request_session_transition(%s, 'REQUESTED', 'analyst', 'idem-x', %s)",
        (session_id, fencing_token),
    )
    assert result["error"] is not None


def test_request_session_transition_allows_operator_and_writes_outbox_atomically(seeded_db):
    seeded_db.execute(
        "insert into evidence_session (actor, idempotency_key) values ('seed', 'idem-seed-2')"
    )
    session_id = seeded_db.execute(
        "select id from evidence_session order by created_at desc limit 1"
    ).fetchone()[0]
    fencing_token = seeded_db.execute(
        "select fencing_token from evidence_session where id = %s", (session_id,)
    ).fetchone()[0]

    claims = json.dumps({"sub": PLATFORM_OPERATOR_ID, "aal": "aal2", "role": "authenticated"})
    with seeded_db.transaction() as tx:
        seeded_db.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
        seeded_db.execute(sql.SQL("set local role {}").format(sql.Identifier("authenticated")))
        seeded_db.execute(
            "select * from request_session_transition(%s, 'REQUESTED', 'operator', "
            "'idem-op', %s)",
            (session_id, fencing_token),
        )
        state = seeded_db.execute(
            "select state from evidence_session where id = %s", (session_id,)
        ).fetchone()[0]
        outbox_count = seeded_db.execute(
            "select count(*) from outbox_events where session_id = %s and target_state = "
            "'REQUESTED'",
            (session_id,),
        ).fetchone()[0]
        raise Rollback(tx)

    assert state == "REQUESTED"
    assert outbox_count == 1


def test_request_session_transition_rejects_caller_with_no_profile_row(seeded_db):
    """current_app_role() returns NULL for a user with no profiles row; the
    role check must not fail open on that NULL (NULL NOT IN (...) is NULL,
    not true)."""
    seeded_db.execute(
        "insert into evidence_session (actor, idempotency_key) values ('seed', 'idem-seed-4')"
    )
    session_id = seeded_db.execute(
        "select id from evidence_session order by created_at desc limit 1"
    ).fetchone()[0]
    fencing_token = seeded_db.execute(
        "select fencing_token from evidence_session where id = %s", (session_id,)
    ).fetchone()[0]

    seeded_db.execute("delete from profiles where user_id = %s", (ANALYST_ID,))

    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal2",
        "select * from request_session_transition(%s, 'REQUESTED', 'no-profile', 'idem-np', %s)",
        (session_id, fencing_token),
    )
    assert result["error"] is not None


def test_destroying_reachable_from_provisioning_via_rpc(seeded_db):
    """Destroy must always be available, including from a wedged mid-provision
    state, not only from READY/CAPTURING."""
    seeded_db.execute(
        "insert into evidence_session (state, actor, idempotency_key) "
        "values ('PROVISIONING', 'seed', 'idem-seed-5')"
    )
    session_id = seeded_db.execute(
        "select id from evidence_session order by created_at desc limit 1"
    ).fetchone()[0]
    fencing_token = seeded_db.execute(
        "select fencing_token from evidence_session where id = %s", (session_id,)
    ).fetchone()[0]

    result = run_as(
        seeded_db,
        PLATFORM_OPERATOR_ID,
        "aal2",
        "select * from request_session_transition(%s, 'DESTROYING', 'operator', "
        "'idem-teardown', %s)",
        (session_id, fencing_token),
    )
    assert result["error"] is None


def test_audit_log_insert_rejects_self_declared_role_mismatch(seeded_db):
    """actor_role must match the caller's real current_app_role(), not an
    arbitrary client-supplied value, or the audit trail is spoofable."""
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "insert into audit_log (actor_id, actor_role, action, resource) "
        "values (%s, 'platform_admin', 'session.destroy', 'evidence_session')",
        (ANALYST_ID,),
    )
    assert result["error"] is not None


def test_request_session_transition_rejects_stale_fencing_token(seeded_db):
    seeded_db.execute(
        "insert into evidence_session (actor, idempotency_key) values ('seed', 'idem-seed-3')"
    )
    session_id = seeded_db.execute(
        "select id from evidence_session order by created_at desc limit 1"
    ).fetchone()[0]

    result = run_as(
        seeded_db,
        PLATFORM_OPERATOR_ID,
        "aal2",
        "select * from request_session_transition(%s, 'REQUESTED', 'operator', 'idem-stale', "
        "'wrong-token')",
        (session_id,),
    )
    assert result["error"] is not None


def test_database_transition_rules_match_the_typescript_contract(seeded_db):
    """The state graph is declared once in session-transitions.json; the
    database seed and the TypeScript contract both read it. Assert they agree
    so the two enforcement points cannot drift apart silently."""
    contract_path = REPO_ROOT / "packages" / "contracts" / "src" / "session-transitions.json"
    expected = {
        (from_state, to_state)
        for from_state, targets in json.loads(contract_path.read_text()).items()
        for to_state in targets
    }
    assert expected, "transition contract must not be empty"

    rows = seeded_db.execute("select from_state, to_state from session_transition_rule").fetchall()
    assert {(row[0], row[1]) for row in rows} == expected


def test_anon_cannot_execute_session_transition_rpc(seeded_db):
    seeded_db.execute(
        "insert into evidence_session (actor, idempotency_key) values ('seed', 'idem-anon')"
    )
    session_id = seeded_db.execute("select id from evidence_session limit 1").fetchone()[0]
    fencing_token = seeded_db.execute(
        "select fencing_token from evidence_session where id = %s", (session_id,)
    ).fetchone()[0]

    result = run_as(
        seeded_db,
        None,
        "aal1",
        "select * from request_session_transition(%s, 'REQUESTED', 'anon', 'idem-a', %s)",
        (session_id, fencing_token),
        pg_role="anon",
    )
    assert result["error"] is not None


def test_reusing_an_idempotency_key_for_a_different_target_is_rejected(seeded_db):
    seeded_db.execute(
        "insert into evidence_session (actor, idempotency_key, state) "
        "values ('seed', 'idem-reuse', 'REQUESTED')"
    )
    session_id = seeded_db.execute("select id from evidence_session limit 1").fetchone()[0]
    fencing_token = seeded_db.execute(
        "select fencing_token from evidence_session where id = %s", (session_id,)
    ).fetchone()[0]

    result = run_as(
        seeded_db,
        PLATFORM_OPERATOR_ID,
        "aal2",
        "select * from request_session_transition(%s, 'PROVISIONING', 'operator', "
        "'idem-reuse', %s)",
        (session_id, fencing_token),
    )
    assert result["error"] is not None


def test_replaying_the_same_key_and_target_is_idempotent(seeded_db):
    seeded_db.execute(
        "insert into evidence_session (actor, idempotency_key, state) "
        "values ('seed', 'idem-replay', 'REQUESTED')"
    )
    session_id = seeded_db.execute("select id from evidence_session limit 1").fetchone()[0]

    result = run_as(
        seeded_db,
        PLATFORM_OPERATOR_ID,
        "aal2",
        "select version from request_session_transition(%s, 'REQUESTED', 'operator', "
        "'idem-replay', 'any-token')",
        (session_id,),
    )
    assert result["error"] is None
    assert result["rows"][0][0] == 1


def test_analyst_can_update_and_delete_own_report(seeded_db):
    seeded_db.execute(
        "insert into saved_reports (owner_id, company_id, payload) "
        "values (%s, 'ACME', '{}'::jsonb)",
        (ANALYST_ID,),
    )
    report_id = seeded_db.execute("select id from saved_reports limit 1").fetchone()[0]

    updated = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "update saved_reports set company_id = 'ACME2' where id = %s returning company_id",
        (report_id,),
    )
    assert updated["rows"] == [("ACME2",)]

    deleted = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "delete from saved_reports where id = %s returning id",
        (report_id,),
    )
    assert deleted["rows"] == [(report_id,)]


def test_analyst_cannot_delete_another_users_report(seeded_db):
    seeded_db.execute(
        "insert into saved_reports (owner_id, company_id, payload) "
        "values (%s, 'ACME', '{}'::jsonb)",
        (OTHER_ANALYST_ID,),
    )
    report_id = seeded_db.execute("select id from saved_reports limit 1").fetchone()[0]

    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "delete from saved_reports where id = %s returning id",
        (report_id,),
    )
    assert result["rows"] == []


# ---------------------------------------------------------------------------
# AI budget persistence (ai_request_usage + consume_ai_quota + record_audit_event)
# ---------------------------------------------------------------------------

AI_QUOTA_SQL = """
select * from consume_ai_quota(2, interval '24 hours', 5, interval '60 seconds')
"""


def _consume_as(conn, user_id, aal="aal1", quota_sql=AI_QUOTA_SQL):
    """Run consume_ai_quota as `user_id` in a committed transaction and return
    its rows, leaving the resulting usage rows persisted for later reads."""
    claims = json.dumps({"sub": user_id, "aal": aal, "role": "authenticated"})
    with conn.transaction():
        conn.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
        cur = conn.execute(quota_sql)
        return cur.fetchall()


def _audit_as(conn, user_id, args, metadata_sql, aal="aal1"):
    """Run record_audit_event(...) as `user_id` in a committed transaction and
    return its rows, leaving the audit row persisted for later reads."""
    claims = json.dumps({"sub": user_id, "aal": aal, "role": "authenticated"})
    with conn.transaction():
        conn.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
        cur = conn.execute(f"select record_audit_event({args}, {metadata_sql})")
        return cur.fetchall()


def test_analyst_can_read_own_usage_row(seeded_db):
    # Seed one usage row owned by the analyst via the committed RPC.
    _consume_as(seeded_db, ANALYST_ID)
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "select distinct user_id from ai_request_usage",
    )
    assert result["error"] is None
    assert {str(r[0]) for r in result["rows"]} == {ANALYST_ID}


def test_analyst_cannot_read_another_users_usage(seeded_db):
    # Seed a row owned by another analyst (committed, so it persists).
    _consume_as(seeded_db, OTHER_ANALYST_ID)
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "select user_id from ai_request_usage",
    )
    # RLS filters to the caller's own rows: ANALYST_ID sees zero rows.
    assert result["error"] is None
    assert result["rows"] == []


def test_analyst_cannot_insert_usage_directly(seeded_db):
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "insert into ai_request_usage (user_id, kind, window_start, used) "
        "values (%s, 'QUOTA', now(), 0)",
        (ANALYST_ID,),
    )
    assert result["error"] is not None


def test_analyst_cannot_update_usage_directly(seeded_db):
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "update ai_request_usage set used = 0",
    )
    assert result["error"] is not None


def test_consume_ai_quota_increments_by_one_when_allowed(seeded_db):
    rows = _consume_as(seeded_db, ANALYST_ID)
    assert rows[0][0] is True  # allowed
    assert rows[0][1] is None  # denial
    assert rows[0][2] == 1  # quota_used
    assert rows[0][3] == 2  # quota_limit


def test_consume_ai_quota_denies_at_the_limit_without_incrementing(seeded_db):
    # Exhaust the quota (limit 2): two allowed calls fill it.
    _consume_as(seeded_db, ANALYST_ID)
    _consume_as(seeded_db, ANALYST_ID)

    rows = _consume_as(seeded_db, ANALYST_ID)
    row = rows[0]
    assert row[0] is False
    assert row[1] == "QUOTA_EXHAUSTED"
    assert row[2] == 2  # quota_used unchanged, still at the limit

    # A refused request must not spend the analyst's budget further.
    remaining = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "select used from ai_request_usage " "where user_id = %s and kind = 'QUOTA'",
        (ANALYST_ID,),
    )
    assert remaining["rows"] == [(2,)]


def test_concurrent_requests_with_one_unit_remaining_allow_exactly_one(seeded_db, pg_cluster):
    """Two connections race for the quota's last unit; exactly one must pass,
    proving consume_ai_quota serializes on the counter row."""
    from concurrent.futures import ThreadPoolExecutor

    import psycopg

    # Leave the analyst one quota unit remaining (limit 2, consume once).
    _consume_as(seeded_db, ANALYST_ID)
    claims = json.dumps({"sub": ANALYST_ID, "aal": "aal1", "role": "authenticated"})

    def race() -> bool:
        conn = psycopg.connect(
            dbname="phase2_rls_test",
            user="postgres",
            host=pg_cluster["host"],
            autocommit=True,
        )
        try:
            # set_config(..., is_local=true) only lasts for the transaction, so
            # the claim and the RPC must share a transaction block.
            with conn.transaction():
                conn.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
                cur = conn.execute(AI_QUOTA_SQL)
                return bool(cur.fetchone()[0])
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: race(), [0, 1]))

    assert sorted(results) == [False, True]


def test_record_audit_event_rejects_a_non_whitelisted_metadata_key(seeded_db):
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "select record_audit_event('ai.request', 'ALLOWED', 'NVL', "
        '\'{"secret": "should be rejected"}\'::jsonb)',
    )
    assert result["error"] is not None
    count = seeded_db.execute("select count(*) from audit_log").fetchone()[0]
    assert count == 0


def test_record_audit_event_rejects_a_compound_metadata_value(seeded_db):
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "select record_audit_event('ai.request', 'ALLOWED', 'NVL', "
        '\'{"reason": {"body": "hidden prompt"}}\'::jsonb)',
    )
    assert result["error"] is not None
    count = seeded_db.execute("select count(*) from audit_log").fetchone()[0]
    assert count == 0


def test_record_audit_event_writes_a_row_without_prompt_text(seeded_db):
    rows = _audit_as(
        seeded_db,
        ANALYST_ID,
        "'ai.request', 'ALLOWED', 'HPG'",
        "'{\"quota_remaining\": 18}'::jsonb",
    )
    assert rows[0][0] is not None  # returned audit id
    row = seeded_db.execute(
        "select actor_id, actor_role, action, resource, metadata from audit_log"
    ).fetchone()
    assert str(row[0]) == ANALYST_ID
    assert row[1] == "analyst"  # pinned to the caller's real role
    assert row[2] == "ai.request"
    assert row[3] == "HPG"
    assert row[4]["outcome"] == "ALLOWED"
    assert row[4]["quota_remaining"] == 18


def test_platform_viewer_can_read_audit_log(seeded_db):
    _audit_as(seeded_db, ANALYST_ID, "'ai.request', 'ALLOWED', 'HPG'", "'{}'::jsonb")
    result = run_as(
        seeded_db,
        PLATFORM_VIEWER_ID,
        "aal2",
        "select action from audit_log",
    )
    assert result["error"] is None
    assert result["rows"] == [("ai.request",)]


def test_analyst_cannot_read_another_users_audit_log(seeded_db):
    _audit_as(seeded_db, OTHER_ANALYST_ID, "'ai.request', 'ALLOWED', 'HPG'", "'{}'::jsonb")
    result = run_as(
        seeded_db,
        ANALYST_ID,
        "aal1",
        "select action from audit_log",
    )
    assert result["rows"] == []


def test_anon_cannot_execute_consume_ai_quota(seeded_db):
    result = run_as(
        seeded_db,
        None,
        "aal1",
        AI_QUOTA_SQL,
        pg_role="anon",
    )
    assert result["error"] is not None


def test_anon_cannot_execute_record_audit_event(seeded_db):
    result = run_as(
        seeded_db,
        None,
        "aal1",
        "select record_audit_event('ai.request', 'ALLOWED', 'HPG', '{}'::jsonb)",
        pg_role="anon",
    )
    assert result["error"] is not None
