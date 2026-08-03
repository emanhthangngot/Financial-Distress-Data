"""RLS/RBAC tests for every role/action pair in phase-02's Authorization Model.

Runs against a real (ephemeral, native) Postgres server with the actual
Phase 2 migrations applied — no mocked database.
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
