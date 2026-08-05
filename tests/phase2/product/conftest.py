"""Ephemeral Postgres cluster for Phase 2 RLS/RBAC tests.

Docker networking is unavailable in this sandbox (veth pair creation fails),
so `supabase start` cannot be used here. This fixture drives the native
`initdb`/`pg_ctl` binaries directly and stubs the subset of Supabase's `auth`
schema (`auth.uid()`, `auth.jwt()`) that our RLS policies depend on, so the
real migration SQL is exercised against a real Postgres server rather than
mocked.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import Rollback, sql

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"

AUTH_STUB_SQL = """
create schema if not exists auth;

create table if not exists auth.users (
  id uuid primary key,
  email text
);

create or replace function auth.jwt() returns jsonb
language sql stable
as $$
  select nullif(current_setting('request.jwt.claims', true), '')::jsonb
$$;

create or replace function auth.uid() returns uuid
language sql stable
as $$
  select nullif(auth.jwt() ->> 'sub', '')::uuid
$$;
"""


@pytest.fixture(scope="session")
def pg_cluster(tmp_path_factory: pytest.TempPathFactory):
    for binary in ("initdb", "pg_ctl", "psql"):
        if shutil.which(binary) is None:
            message = f"{binary} not available; cannot run real-Postgres RLS tests"
            # A silent skip in CI would mean the authorization rules are never
            # actually verified anywhere. CI sets PHASE2_REQUIRE_PG=1 so a
            # missing server is a failure there, not a quiet pass.
            if os.environ.get("PHASE2_REQUIRE_PG") == "1":
                pytest.fail(message)
            pytest.skip(message)

    data_dir = tmp_path_factory.mktemp("phase2-pgdata")
    socket_dir = tmp_path_factory.mktemp("phase2-pgsocket")
    log_file = data_dir / "server.log"

    subprocess.run(
        ["initdb", "-D", str(data_dir), "-U", "postgres", "-A", "trust"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "pg_ctl",
            "-D",
            str(data_dir),
            "-o",
            f"-k {socket_dir} -h '' -c listen_addresses=''",
            "-l",
            str(log_file),
            "start",
        ],
        check=True,
        capture_output=True,
    )
    try:
        for _ in range(50):
            try:
                with psycopg.connect(dbname="postgres", user="postgres", host=str(socket_dir)):
                    break
            except psycopg.OperationalError:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"Postgres did not become ready; see {log_file}")

        yield {"host": str(socket_dir)}
    finally:
        subprocess.run(
            ["pg_ctl", "-D", str(data_dir), "-m", "immediate", "stop"],
            capture_output=True,
        )


@pytest.fixture(scope="session")
def phase2_conn(pg_cluster: dict[str, str]):
    admin_conn = psycopg.connect(
        dbname="postgres", user="postgres", host=pg_cluster["host"], autocommit=True
    )
    admin_conn.execute("drop database if exists phase2_rls_test")
    admin_conn.execute("create database phase2_rls_test")
    admin_conn.close()

    conn = psycopg.connect(
        dbname="phase2_rls_test", user="postgres", host=pg_cluster["host"], autocommit=True
    )
    conn.execute(AUTH_STUB_SQL)

    # Real Supabase projects have `anon`/`authenticated`/`service_role` in
    # place before any migration runs; create them first so the migrations'
    # own `grant`/`revoke` statements land on roles that already exist, same
    # as production, instead of us hand-granting privileges the migrations
    # don't actually declare.
    conn.execute("create role anon noinherit nologin")
    conn.execute("create role authenticated noinherit nologin")
    conn.execute("create role service_role noinherit nologin bypassrls")
    conn.execute("grant usage on schema public, auth to anon, authenticated, service_role")

    # Supabase ships default privileges that grant every new public table to
    # anon and authenticated. Reproducing that here is what makes the tests
    # honest: without it the migrations would look secure purely because this
    # harness never handed out the privilege in the first place, and a direct
    # client write would appear blocked in tests while succeeding in
    # production.
    conn.execute(
        "alter default privileges in schema public "
        "grant all on tables to anon, authenticated, service_role"
    )
    conn.execute(
        "alter default privileges in schema public "
        "grant all on functions to anon, authenticated, service_role"
    )

    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.execute(migration.read_text())

    yield conn
    conn.close()


ANALYST_ID = "00000000-0000-0000-0000-000000000001"
PLATFORM_VIEWER_ID = "00000000-0000-0000-0000-000000000002"
PLATFORM_OPERATOR_ID = "00000000-0000-0000-0000-000000000003"
PLATFORM_ADMIN_ID = "00000000-0000-0000-0000-000000000004"
OTHER_ANALYST_ID = "00000000-0000-0000-0000-000000000005"

SEED_USERS: tuple[tuple[str, str], ...] = (
    (ANALYST_ID, "analyst"),
    (PLATFORM_VIEWER_ID, "platform_viewer"),
    (PLATFORM_OPERATOR_ID, "platform_operator"),
    (PLATFORM_ADMIN_ID, "platform_admin"),
    (OTHER_ANALYST_ID, "analyst"),
)


@pytest.fixture()
def seeded_db(phase2_conn: psycopg.Connection):
    """Reset seed rows before each test so tests stay independent."""
    phase2_conn.execute(
        "truncate audit_log, saved_reports, outbox_events, ai_request_usage, "
        "evidence_session_transition, evidence_session, profiles cascade"
    )
    phase2_conn.execute("delete from auth.users")
    for user_id, role in SEED_USERS:
        phase2_conn.execute(
            "insert into auth.users (id, email) values (%s, %s)", (user_id, f"{role}@test")
        )
        phase2_conn.execute("update profiles set role = %s where user_id = %s", (role, user_id))
    yield phase2_conn


def run_as(
    conn: psycopg.Connection,
    user_id: str | None,
    aal: str,
    query: str,
    params: tuple[Any, ...] | None = None,
    pg_role: str = "authenticated",
) -> dict[str, Any]:
    """Execute `query` as `pg_role` (default `authenticated`) with the given
    JWT claims, always rolling back so scenarios never leak state into one
    another. Pass `pg_role="anon"` and `user_id=None` to test the anonymous
    (no session) path."""
    outcome: dict[str, Any] = {"rows": None, "error": None}
    claims = json.dumps({"sub": user_id, "aal": aal, "role": pg_role})
    with conn.transaction() as tx:
        conn.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
        conn.execute(sql.SQL("set local role {}").format(sql.Identifier(pg_role)))
        try:
            cur = conn.execute(query, params)
            outcome["rows"] = cur.fetchall() if cur.description else None
        except Exception as exc:  # noqa: BLE001 - capturing for assertion, not swallowing silently
            outcome["error"] = exc
        raise Rollback(tx)
    return outcome
