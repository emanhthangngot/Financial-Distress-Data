#!/usr/bin/env bash
set -u

failures=0

pass() { printf 'PASS %-22s %s\n' "$1" "$2"; }
fail() { printf 'FAIL %-22s %s\n' "$1" "$2"; failures=$((failures + 1)); }

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    pass "command:$1" "$(command -v "$1")"
  else
    fail "command:$1" "not found"
  fi
}

for command in docker git python uv; do
  check_command "$command"
done

if docker compose version >/dev/null 2>&1; then
  pass "docker-compose" "$(docker compose version --short)"
else
  fail "docker-compose" "Docker Compose v2 is unavailable"
fi

cpu_count="$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf 0)"
if [ "$cpu_count" -ge 4 ]; then
  pass "cpu" "${cpu_count} logical CPUs"
else
  fail "cpu" "${cpu_count} logical CPUs; at least 4 required"
fi

memory_kib="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || printf 0)"
if [ "$memory_kib" -ge 8388608 ]; then
  pass "memory" "$((memory_kib / 1024)) MiB"
else
  fail "memory" "$((memory_kib / 1024)) MiB; at least 8192 MiB required"
fi

available_kib="$(df -Pk . | awk 'NR == 2 {print $4}')"
if [ "$available_kib" -ge 8388608 ]; then
  pass "disk" "$((available_kib / 1024)) MiB available"
else
  fail "disk" "$((available_kib / 1024)) MiB available; at least 8192 MiB required"
fi

for required in docker-compose.yml configs/rubric-requirements.yaml uv.lock; do
  if [ -f "$required" ]; then
    pass "file" "$required"
  else
    fail "file" "$required is missing"
  fi
done

if docker compose config --quiet >/dev/null 2>&1; then
  pass "compose-config" "valid"
else
  fail "compose-config" "docker compose config failed"
fi

if [ "$failures" -ne 0 ]; then
  printf '\nPreflight failed with %s error(s).\n' "$failures"
  exit 1
fi

printf '\nClean-room preflight passed.\n'
