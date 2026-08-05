"""Outbox worker lease/fencing integration tests.

Runs against the same ephemeral real Postgres as the RLS suite
(`conftest.py::phase2_conn`). Unlike `test_rbac_rls.py`, these tests commit
their writes instead of rolling back — the lease/fencing guarantees only mean
something across separate, persisted claims, which is exactly what two
independent worker processes would do.
"""

from __future__ import annotations

import json
import time
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .conftest import PLATFORM_OPERATOR_ID


def run_committed(
    conn: psycopg.Connection,
    user_id: str | None,
    aal: str,
    query: str,
    params: tuple[Any, ...] | None = None,
    pg_role: str = "authenticated",
) -> dict[str, Any]:
    """Like `run_as`, but commits instead of rolling back — this module needs
    state (claimed events, rotated fencing tokens) to persist across calls
    the way it would across separate worker processes."""
    outcome: dict[str, Any] = {"rows": None, "error": None}
    claims = json.dumps({"sub": user_id, "aal": aal, "role": pg_role})
    conn.execute("select set_config('request.jwt.claims', %s, false)", (claims,))
    conn.execute("set role " + pg_role)
    try:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(query, params)
        outcome["rows"] = cur.fetchall() if cur.description else None
    except Exception as exc:  # noqa: BLE001 - captured for assertion
        outcome["error"] = exc
    finally:
        conn.execute("reset role")
    return outcome


def operator(
    conn: psycopg.Connection, query: str, params: tuple[Any, ...] | None = None
) -> dict[str, Any]:
    return run_committed(conn, PLATFORM_OPERATOR_ID, "aal2", query, params)


def worker(
    conn: psycopg.Connection, query: str, params: tuple[Any, ...] | None = None
) -> dict[str, Any]:
    """The outbox worker holds the service-role key, not a user JWT — there is
    no analyst/operator identity or AAL behind a claim/complete/fail call."""
    return run_committed(conn, None, "aal1", query, params, pg_role="service_role")


def create_session(conn: psycopg.Connection, idempotency_key: str) -> dict[str, Any]:
    result = operator(
        conn,
        "select * from create_evidence_session(%s, %s)",
        ("operator@test", idempotency_key),
    )
    assert result["error"] is None, result["error"]
    return result["rows"][0]


def transition(
    conn: psycopg.Connection,
    session_id: str,
    target_state: str,
    idempotency_key: str,
    fencing_token: str,
) -> dict[str, Any]:
    return operator(
        conn,
        "select * from request_session_transition(%s, %s, %s, %s, %s)",
        (session_id, target_state, "operator@test", idempotency_key, fencing_token),
    )


def claim(
    conn: psycopg.Connection, worker_id: str, limit: int = 5, lease_seconds: int = 120
) -> list[dict[str, Any]]:
    result = worker(
        conn,
        "select * from claim_outbox_events(%s, %s, %s)",
        (worker_id, limit, lease_seconds),
    )
    assert result["error"] is None, result["error"]
    return result["rows"]


def complete(
    conn: psycopg.Connection, event_id: str, worker_id: str, outcome: str
) -> dict[str, Any]:
    return worker(
        conn,
        "select * from complete_outbox_event(%s, %s, %s)",
        (event_id, worker_id, outcome),
    )


def fail(
    conn: psycopg.Connection, event_id: str, worker_id: str, error: str, max_attempts: int = 5
) -> dict[str, Any]:
    return worker(
        conn,
        "select * from fail_outbox_event(%s, %s, %s, %s)",
        (event_id, worker_id, error, max_attempts),
    )


def test_two_workers_claim_disjoint_event_sets(seeded_db):
    session_a = create_session(seeded_db, "outbox-disjoint-a")
    session_b = create_session(seeded_db, "outbox-disjoint-b")
    for session in (session_a, session_b):
        transition_result = transition(
            seeded_db,
            session["id"],
            "REQUESTED",
            f"{session['idempotency_key']}-req",
            session["fencing_token"],
        )
        assert transition_result["error"] is None, transition_result["error"]

    w1_events = claim(seeded_db, "worker-1", limit=1)
    w2_events = claim(seeded_db, "worker-2", limit=5)

    assert len(w1_events) == 1
    w1_ids = {row["id"] for row in w1_events}
    w2_ids = {row["id"] for row in w2_events}
    assert w1_ids.isdisjoint(w2_ids)
    # Every event any worker claimed belongs to one of the two sessions we created.
    session_ids = {session_a["id"], session_b["id"]}
    for row in [*w1_events, *w2_events]:
        assert row["session_id"] in session_ids


def test_expired_lease_returns_event_to_pool(seeded_db):
    session = create_session(seeded_db, "outbox-expired-lease")
    transition(
        seeded_db,
        session["id"],
        "REQUESTED",
        f"{session['idempotency_key']}-req",
        session["fencing_token"],
    )

    first_claim = claim(seeded_db, "worker-stale", limit=1, lease_seconds=1)
    assert len(first_claim) == 1
    event_id = first_claim[0]["id"]

    # Immediately reclaiming must not see it — the lease has not expired yet.
    still_leased = claim(seeded_db, "worker-fresh", limit=5)
    assert event_id not in {row["id"] for row in still_leased}

    time.sleep(1.2)

    reclaimed = claim(seeded_db, "worker-fresh", limit=5)
    assert event_id in {row["id"] for row in reclaimed}


def test_completion_after_superseding_transition_is_stale_fencing(seeded_db):
    session = create_session(seeded_db, "outbox-stale-fencing")
    first = transition(
        seeded_db,
        session["id"],
        "REQUESTED",
        f"{session['idempotency_key']}-req",
        session["fencing_token"],
    )
    assert first["error"] is None, first["error"]
    updated_session = first["rows"][0]

    claimed = claim(seeded_db, "worker-race", limit=5)
    event = next(row for row in claimed if row["session_id"] == session["id"])

    # A second transition rotates the session's fencing token underneath the
    # worker's in-flight claim, simulating an operator retrying/cancelling
    # while the worker is still processing the superseded event.
    second = transition(
        seeded_db,
        session["id"],
        "DESTROYING",
        f"{session['idempotency_key']}-destroy",
        updated_session["fencing_token"],
    )
    assert second["error"] is None, second["error"]

    # complete_outbox_event returns the FAILED row rather than raising: an
    # exception here would abort the call's implicit transaction and roll
    # back the very mark it is supposed to leave behind.
    completion = complete(seeded_db, event["id"], "worker-race", "provisioned")
    assert completion["error"] is None, completion["error"]
    assert completion["rows"][0]["status"] == "FAILED"
    assert "stale fencing token" in completion["rows"][0]["last_error"]

    row = operator(seeded_db, "select status from outbox_events where id = %s", (event["id"],))
    assert row["rows"][0]["status"] == "FAILED"

    session_row = operator(
        seeded_db, "select state from evidence_session where id = %s", (session["id"],)
    )
    assert session_row["rows"][0]["state"] == "DESTROYING"


def test_fail_below_max_attempts_returns_to_pending(seeded_db):
    session = create_session(seeded_db, "outbox-retry-below-cap")
    transition(
        seeded_db,
        session["id"],
        "REQUESTED",
        f"{session['idempotency_key']}-req",
        session["fencing_token"],
    )
    claimed = claim(seeded_db, "worker-flaky", limit=5)
    event = next(row for row in claimed if row["session_id"] == session["id"])

    result = fail(seeded_db, event["id"], "worker-flaky", "transient error", max_attempts=5)
    assert result["error"] is None, result["error"]
    assert result["rows"][0]["status"] == "PENDING"


def test_fail_beyond_max_attempts_stays_failed(seeded_db):
    session = create_session(seeded_db, "outbox-retry-cap")
    transition(
        seeded_db,
        session["id"],
        "REQUESTED",
        f"{session['idempotency_key']}-req",
        session["fencing_token"],
    )

    event_id: str | None = None
    for attempt in range(1, 3):
        claimed = claim(seeded_db, "worker-poison", limit=5, lease_seconds=1)
        matching = [row for row in claimed if row["session_id"] == session["id"]]
        if matching:
            event_id = matching[0]["id"]
        result = fail(seeded_db, event_id, "worker-poison", "poison event", max_attempts=2)
        assert result["error"] is None, result["error"]
        if attempt < 2:
            assert result["rows"][0]["status"] == "PENDING"
            time.sleep(1.2)  # let the lease expire so the next claim can reclaim it
        else:
            assert result["rows"][0]["status"] == "FAILED"
