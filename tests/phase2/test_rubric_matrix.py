"""Test the Phase 2 rubric matrix and evidence contract linter.

All tests must fail first (SDD test-seed rule) before the supporting
implementation exists — a meaningful failure, not an import error.

Validate:
  - Every scored row has required fields.
  - Total points: ML 100, LLM 100.
  - Semantic IDs are unique and stable (no spreadsheet line numbers).
  - Acceptance criteria are in WHO -> ACTION -> RESULT format.
  - Phase 1 contracts are not mutated.
  - Class contracts exist (src/ml/contracts.py, src/llm/contracts.py).
  - Novel ideas are documented.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_CSV = REPO_ROOT / "docs" / "phase2" / "rubric-matrix.csv"
PHASE1_PROTECTED = [
    "src/collectors/",
    "src/transforms/",
    "src/quality/",
    "src/catalog/",
    "src/metadata/",
    "src/streaming/",
    "src/generator/",
    "dags/",
    "sql/",
    "docs/01_data_generator.md",
    "docs/02_schema_design.md",
    "docs/evidence/",
    "docs/mini_coursework.md",
    "tests/test_stage1",
]

# ── Phase 2 evidence_audit script ───────────────────────────────────────
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_phase2_evidence.py"


class TestPhase1ContractNoMutation:
    """Phase 1 must not be mutated by Phase 2 matrix or linter."""

    def test_audit_script_exists(self) -> None:
        """audit_phase2_evidence.py must exist before Phase 2 gates can run."""
        assert (
            AUDIT_SCRIPT.exists()
        ), f"{AUDIT_SCRIPT} missing — create scripts/audit_phase2_evidence.py"

    def test_no_protected_paths_in_matrix(self) -> None:
        """Matrix MUST NOT claim to modify Phase 1 protected paths."""
        if not MATRIX_CSV.exists():
            pytest.fail(f"{MATRIX_CSV} missing — run 'scripts/_phase2_rubric_items.py' first")
        text = MATRIX_CSV.read_text(encoding="utf-8").lower()
        for path in PHASE1_PROTECTED:
            if path.lower() in text:
                pytest.fail(
                    f"Matrix references Phase 1 protected path '{path}' — "
                    "Phase 2 must not mutate Phase 1."
                )

    def test_phase1_mutation_from_changed_paths(self) -> None:
        """A git diff that touches a Phase 1 path must be flagged."""
        import importlib.util

        if not AUDIT_SCRIPT.exists():
            pytest.fail("audit script missing")
        spec = importlib.util.spec_from_file_location("audit_phase2", AUDIT_SCRIPT)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # A diff touching a collector must fail
        errors = mod._phase1_mutation_from_changed(["src/collectors/some_adapter.py"])
        assert any("src/collectors/" in e for e in errors)

        # A diff touching only Phase 2 files must pass
        ok = mod._phase1_mutation_from_changed(
            ["docs/phase2/architecture.md", "scripts/audit_phase2_evidence.py"]
        )
        assert ok == [], f"expected no Phase 1 mutation, got {ok}"


class TestRubricMatrix:
    """Validate rubric matrix completeness and invariants."""

    def test_matrix_csv_exists(self) -> None:
        """rubric-matrix.csv must exist."""
        assert (
            MATRIX_CSV.exists()
        ), f"{MATRIX_CSV} not found — create it via scripts/_phase2_rubric_items.py"

    def test_ml_100_points(self) -> None:
        """ML track must total exactly 100 points."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.fail("Matrix CSV missing")
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        total = 0
        for row in reader:
            if row.get("track") == "ML":
                try:
                    total += int(row.get("points", "0"))
                except ValueError:
                    pass
        assert total == 100, f"ML points = {total}, expected 100"

    def test_llm_100_points(self) -> None:
        """LLM track must total exactly 100 points."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.fail("Matrix CSV missing")
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        total = 0
        for row in reader:
            if row.get("track") == "LLM":
                try:
                    total += int(row.get("points", "0"))
                except (ValueError, KeyError):
                    pass
        assert total == 100, f"LLM points = {total}, expected 100"

    def test_every_scored_row_has_all_required_fields(self) -> None:
        """Every scored row must have rubric_id, requirement, proof,
        deliverables, owner, test (validation command), evidence_path,
        evidence_type."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        required = [
            "rubric_id",
            "track",
            "points",
            "requirement",
            "proof",
            "deliverables",
            "owner",
            "test",
            "evidence_path",
            "evidence_type",
            "artifact_path",
        ]
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        missing: list[str] = []
        for row in reader:
            rid = row.get("rubric_id", "?")
            for field in required:
                if not row.get(field, "").strip():
                    missing.append(f"{rid}: missing '{field}'")
        assert not missing, "\n".join(missing)

    def test_every_validation_command_is_reproducible(self) -> None:
        """Every row's test field must be a runnable pytest invocation."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        bad: list[str] = []
        for row in reader:
            test = row.get("test", "")
            if not test.startswith("pytest tests/phase2"):
                bad.append(f"{row.get('rubric_id','?')}: test='{test}' not reproducible")
        assert not bad, "\n".join(bad)

    def test_every_role_owns_scored_rows(self) -> None:
        """All four roles must own at least one scored row."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        roles = {"ml_engineer", "llm_engineer", "data_engineer", "platform_operator"}
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        seen: set[str] = set()
        for row in reader:
            owner = row.get("owner", "")
            if owner:
                seen.add(owner)
        missing_roles = roles - seen
        assert not missing_roles, f"Roles owning no scored row: {sorted(missing_roles)}"

    def test_semantic_ids_unique_and_stable(self) -> None:
        """IDs must be unique and must not contain spreadsheet line numbers."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        seen: set[str] = set()
        for row in reader:
            rid = row.get("rubric_id", "")
            if rid in seen:
                pytest.fail(f"Duplicate rubric_id: {rid}")
            seen.add(rid)
            # No line-number suffix
            if re.search(r"row[-_]?\d+$", rid):
                pytest.fail(
                    f"rubric_id '{rid}' contains spreadsheet line number — uses semantic slug"
                )

    def test_evidence_type_valid(self) -> None:
        """All evidence_type values must be in {executed, design_only, stretch}."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        valid = {"executed", "design_only", "stretch"}
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        for row in reader:
            etype = row.get("evidence_type", "")
            if etype not in valid:
                pytest.fail(f"{row.get('rubric_id','?')}: evidence_type='{etype}' not in {valid}")

    def test_owner_is_role_based(self) -> None:
        """Owner must be one of the defined roles."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        roles = {"ml_engineer", "llm_engineer", "data_engineer", "platform_operator"}
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        for row in reader:
            owner = row.get("owner", "")
            if owner and owner not in roles:
                pytest.fail(f"{row.get('rubric_id','?')}: owner '{owner}' not a recognized role")

    def test_evidence_paths_in_phase2_evidence_dir(self) -> None:
        """All planned evidence_path must be under docs/phase2/evidence/."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        for row in reader:
            epath = row.get("evidence_path", "")
            if epath and not epath.startswith("docs/phase2/evidence/"):
                pytest.fail(
                    f"{row.get('rubric_id','?')}: evidence_path='{epath}' "
                    "not under docs/phase2/evidence/"
                )

    def test_artifact_paths_under_allowed_roots(self) -> None:
        """Every row's artifact_path must name an exact implementation path.

        P1-1: per-row validation must not be a metadata-only false positive.
        Each rubric row must map to a concrete Phase 2 implementation artifact
        (requirements.md section 2: src/ml/, src/drift/, src/llm/, src/agents/,
        apps/), and the path must end in the rubric_id so a reviewer finds it
        without inference.
        """
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        roots = ("src/ml/", "src/drift/", "src/llm/", "src/agents/", "apps/")
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        used: set[str] = set()
        for row in reader:
            rid = row.get("rubric_id", "?")
            apath = row.get("artifact_path", "")
            assert apath, f"{rid}: missing artifact_path (exact implementation)"
            assert apath.startswith(
                roots
            ), f"{rid}: artifact_path='{apath}' not under an allowed Phase 2 root"
            assert apath.endswith(rid), f"{rid}: artifact_path must end with the rubric_id"
            used.add(next(r for r in roots if apath.startswith(r)))
        # At least one row must map to each implementation root (P1-1 domain map).
        assert len(used) == 5, f"artifact_paths must cover all 5 roots: {sorted(used)}"


class TestAcceptanceCriteria:
    """AC must be in WHO -> ACTION -> RESULT format."""

    def test_acceptance_criteria_doc_exists(self) -> None:
        """docs/phase2/requirements.md must have per-deliverable ACs."""
        reqs_md = REPO_ROOT / "docs" / "phase2" / "requirements.md"
        assert reqs_md.exists(), (
            f"{reqs_md} not found — write per-deliverable AA in" " WHO -> ACTION -> RESULT form"
        )

    def test_acceptance_criteria_in_who_action_result(self) -> None:
        """At least one acceptance criterion follows WHO -> ACTION -> RESULT pattern."""
        reqs_md = REPO_ROOT / "docs" / "phase2" / "requirements.md"
        if not reqs_md.exists():
            pytest.xfail("requirements.md not yet created")
        text = reqs_md.read_text(encoding="utf-8")
        # WHO → ACTION → RESULT detection: a line with two arrows
        found = re.search(r"\s*->\s*.+->\s*.+", text)
        assert found, (
            "No WHO -> ACTION -> RESULT acceptance criterion found in "
            "docs/phase2/requirements.md"
        )


class TestClassContracts:
    """Five ML + five LLM class contracts must exist with exact signatures."""

    # Contract class -> {method: parameter names (excluding self)}. Locked in
    # docs/phase2/low-level-design.md and mirrored by src/{ml,llm}/contracts.py.
    ML_CONTRACTS = {
        "TrainingDataService": {
            "read_historical_features": ["feature_view", "entity_rows"],
            "join_labels": ["features", "label_table"],
            "validate_schema": ["df"],
            "snapshot_lineage": ["df"],
        },
        "PointInTimeSplitService": {
            "get_split_boundaries": ["df"],
            "split_by_time": ["df"],
            "assert_no_leakage": ["df", "split"],
        },
        "FeatureMaterializationService": {
            "materialize_offline_to_online": ["feature_view", "start_ts", "end_ts"],
            "push_stream_features_offline": ["events"],
            "push_stream_features_online": ["events"],
            "ttl_policy": [],
        },
        "ModelTrainingService": {
            "train": ["train_df", "config"],
            "evaluate": ["model", "validation_df"],
            "log_run": ["model", "metrics", "data_version"],
        },
        "ModelPromotionService": {
            "check_gates": ["candidate_id"],
            "resolve_immutable_uri": ["candidate_id"],
            "open_gitops_pr": ["uri", "image_digest"],
            "rollback_metadata": ["revision"],
        },
    }
    LLM_CONTRACTS = {
        "RagIngestionService": {
            "fetch_documents": ["source", "window"],
            "parse_and_chunk": ["documents"],
            "deduplicate_chunks": ["chunks"],
            "enforce_licensing_and_metadata": ["chunks"],
            "write_vectors": ["chunks", "embedding_version"],
        },
        "EmbeddingRegistryService": {
            "register_version": ["model_name", "dims", "digest"],
            "hot_swap": ["new_version"],
            "resolve_active": [],
            "compatibility_check": ["a", "b"],
        },
        "McpToolService": {
            "authorize": ["tool", "agent_identity", "scope"],
            "invoke": ["tool", "payload"],
            "validate_request": ["payload"],
            "emit_trace": ["tool", "request", "result"],
        },
        "AgentOrchestrationService": {
            "coordinate": ["task", "specialists"],
            "check_citations": ["response"],
            "failure_policy": ["error"],
        },
        "AgentReleaseService": {
            "register": ["agent", "version", "config"],
            "canary": ["agent", "new_version", "fraction"],
            "warm_up": ["agent", "replicas"],
            "promote_or_rollback": ["agent", "decision"],
        },
    }

    @staticmethod
    def _load_contracts(relpath: str):
        import importlib.util

        path = REPO_ROOT / relpath
        assert path.exists(), f"{path} not created — 5 class stubs required"
        spec = importlib.util.spec_from_file_location(
            "phase2_" + relpath.replace("/", "_").replace(".py", ""), path
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _assert_contracts(mod, expected: dict) -> None:
        import abc
        import inspect

        assert len(expected) == 5, f"expected exactly 5 contract classes, got {len(expected)}"
        for cls_name, methods in expected.items():
            cls = getattr(mod, cls_name, None)
            assert cls is not None, f"contract class '{cls_name}' missing from module"
            assert issubclass(cls, abc.ABC), f"'{cls_name}' must be an ABC contract"
            abstract = {
                name
                for name, member in vars(cls).items()
                if getattr(member, "__isabstractmethod__", False)
            }
            assert (
                set(methods) == abstract
            ), f"{cls_name}: abstract methods {sorted(abstract)} != expected {sorted(methods)}"
            for method, params in methods.items():
                signature = inspect.signature(getattr(cls, method))
                actual = [p for p in signature.parameters if p not in ("self", "cls")]
                assert (
                    actual == params
                ), f"{cls_name}.{method}: parameters {actual} != expected {params}"
                doc = inspect.getdoc(getattr(cls, method))
                assert doc, f"{cls_name}.{method} must carry a docstring"

    def test_ml_contract_classes_and_signatures(self) -> None:
        """src/ml/contracts.py must define the 5 ML classes with exact methods."""
        self._assert_contracts(self._load_contracts("src/ml/contracts.py"), self.ML_CONTRACTS)

    def test_llm_contract_classes_and_signatures(self) -> None:
        """src/llm/contracts.py must define the 5 LLM classes with exact methods."""
        self._assert_contracts(self._load_contracts("src/llm/contracts.py"), self.LLM_CONTRACTS)

    def test_ml_low_level_design_doc_exists(self) -> None:
        """docs/phase2/low-level-design.md must document class contracts."""
        path = REPO_ROOT / "docs" / "phase2" / "low-level-design.md"
        assert path.exists(), f"{path} not found"


class TestNovelIdeas:
    """Two novel ideas per track must be documented before Phase 2 code begins."""

    def test_novel_ideas_doc_exists(self) -> None:
        path = REPO_ROOT / "docs" / "phase2" / "novel-ideas.md"
        assert path.exists(), f"{path} not found"

    def test_four_ideas_documented(self) -> None:
        """Exactly 4 novel ideas: 2 ML + 2 LLM, each with a proof path."""
        path = REPO_ROOT / "docs" / "phase2" / "novel-ideas.md"
        if not path.exists():
            pytest.xfail("novel-ideas.md not yet created")
        text = path.read_text(encoding="utf-8")
        flags = re.IGNORECASE | re.MULTILINE
        ml_ideas = len(re.findall(r"^##\s+ML\s+Idea\s+\d+", text, flags=flags))
        llm_ideas = len(re.findall(r"^##\s+LLM\s+Idea\s+\d+", text, flags=flags))
        assert ml_ideas >= 2, f"Expected ≥ 2 ML ideas, found {ml_ideas}"
        assert llm_ideas >= 2, f"Expected ≥ 2 LLM ideas, found {llm_ideas}"
        # Every idea section must name a proof path under docs/phase2/evidence/
        per_idea = text.split("## ML Idea")[1:] + text.split("## LLM Idea")[1:]
        proof_paths = [seg for seg in per_idea if "docs/phase2/evidence/" in seg]
        assert len(proof_paths) == 4, (
            "Each of the 4 ideas must name a proof path under " "docs/phase2/evidence/"
        )


class TestArchitectureDocs:
    """System architecture docs must reflect the Phase 2 two-plane design."""

    def test_phase2_architecture_doc_exists(self) -> None:
        path = REPO_ROOT / "docs" / "phase2" / "architecture.md"
        assert path.exists(), f"{path} not found"

    def test_eight_adrs_exist(self) -> None:
        adr_dir = REPO_ROOT / "docs" / "phase2" / "adr"
        if not adr_dir.exists():
            pytest.fail(f"ADR dir {adr_dir} not found")
        adrs = list(adr_dir.glob("adr-*.md"))
        assert len(adrs) >= 8, f"Expected ≥ 8 ADRs, found {len(adrs)}"

    def test_coursework_doc_rewritten(self) -> None:
        """docs/coursework.md must reference Phase 2 plan, no longer say K8s
        /AWS/LLM are optional."""
        path = REPO_ROOT / "docs" / "coursework.md"
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        must = ["phase-2", "phase2", "Kubernetes"]
        found = any(token.lower() in text.lower() for token in must)
        assert found, "docs/coursework.md has not been updated to Phase 2"


class TestLinterSmoke:
    """Verify the audit script can run and fails on real defects."""

    def test_audit_script_executable(self) -> None:
        import subprocess
        import sys

        if not AUDIT_SCRIPT.exists():
            pytest.xfail("audit script not yet created")
        result = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT), "--matrix-only", "--strict"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"canonical matrix must pass --matrix-only --strict, got {result.returncode}: "
            f"{result.stdout[-400:]}{result.stderr[-200:]}"
        )

    def test_missing_git_base_fails_closed(self) -> None:
        """An unresolvable `--git-base` must fail the gate, not skip it.

        The no-mutation gate is fail-closed: when the baseline cannot be
        verified the auditor exits 1 instead of silently passing with exit 0.
        """
        import subprocess
        import sys

        if not AUDIT_SCRIPT.exists():
            pytest.xfail("audit script not yet created")
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--matrix-only",
                "--strict",
                "--git-base",
                "definitely-missing-ref-zz",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1, (
            f"missing baseline must fail the no-mutation gate, got {result.returncode}: "
            f"{result.stdout[-400:]}"
        )
        assert (
            "baseline" in result.stdout or "git check failed" in result.stdout
        ), f"failure must name the baseline problem, got: {result.stdout[-400:]}"

    def test_incomplete_fixture_fails_with_named_field(self) -> None:
        """An incomplete fixture must fail the linter and name the missing field.

        Uses a real fixture CSV with one scored row that omits 'owner', run
        through the CLI with --matrix, so a missing contract field produces an
        explicit exit-1 failure instead of an accepted exit-0/crash.
        """
        import subprocess
        import sys

        if not AUDIT_SCRIPT.exists():
            pytest.xfail("audit script not yet created")
        fixture = REPO_ROOT / "tests" / "phase2" / "fixtures" / "incomplete-matrix.csv"
        assert fixture.exists(), f"fixture {fixture} not found"
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--matrix-only",
                "--strict",
                "--matrix",
                str(fixture),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1, (
            f"incomplete fixture must fail with exit 1, got {result.returncode}: "
            f"{result.stdout[-400:]}"
        )
        assert (
            "missing 'owner'" in result.stdout
        ), f"failure must name the missing field, got: {result.stdout[-400:]}"

    def test_design_only_fails_require_executed(self) -> None:
        """--require-executed must reject rows still recorded as design_only.

        A design_only row has never been executed, so the phase-08 promotion
        gate fails it instead of letting design work masquerade as completed
        evidence.
        """
        import subprocess
        import sys

        if not AUDIT_SCRIPT.exists():
            pytest.xfail("audit script not yet created")
        fixture = REPO_ROOT / "tests" / "phase2" / "fixtures" / "design-only-matrix.csv"
        assert fixture.exists(), f"fixture {fixture} not found"
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--require-executed",
                "--ml",
                "1",
                "--llm",
                "0",
                "--matrix",
                str(fixture),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1, (
            f"design_only row must fail --require-executed, got {result.returncode}: "
            f"{result.stdout[-400:]}"
        )
        assert (
            "design_only" in result.stdout and "demands executed evidence" in result.stdout
        ), f"failure must name the design_only evidence_type, got: {result.stdout[-400:]}"

    def test_executed_placeholder_fails_evidence_contract(self) -> None:
        """A near-empty evidence file must not satisfy --require-executed.

        The fixture claims evidence_type=executed but the evidence file lacks
        the metadata keys required by docs/phase2/evidence-contract.md, so the
        audit must fail naming the missing keys.
        """
        import subprocess
        import sys

        if not AUDIT_SCRIPT.exists():
            pytest.xfail("audit script not yet created")
        fixture = REPO_ROOT / "tests" / "phase2" / "fixtures" / "executed-incomplete-matrix.csv"
        assert fixture.exists(), f"fixture {fixture} not found"
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--require-executed",
                "--ml",
                "1",
                "--llm",
                "0",
                "--matrix",
                str(fixture),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1, (
            f"placeholder evidence must fail phase-08 audit, got {result.returncode}: "
            f"{result.stdout[-400:]}"
        )
        assert (
            "missing metadata keys" in result.stdout
        ), f"failure must name missing evidence metadata, got: {result.stdout[-400:]}"

    def test_executed_empty_values_fail_evidence_contract(self) -> None:
        """A file with all keys but blank values must not satisfy the audit.

        P1-2: presence of a ``key:`` line is not proof. The evidence file must
        carry a non-empty value for every contract key, otherwise the audit
        fails naming the empty fields.
        """
        import subprocess
        import sys

        if not AUDIT_SCRIPT.exists():
            pytest.xfail("audit script not yet created")
        fixture = REPO_ROOT / "tests" / "phase2" / "fixtures" / "executed-empty-values-matrix.csv"
        assert fixture.exists(), f"fixture {fixture} not found"
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--require-executed",
                "--ml",
                "1",
                "--llm",
                "0",
                "--matrix",
                str(fixture),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1, (
            f"blank evidence values must fail phase-08 audit, got {result.returncode}: "
            f"{result.stdout[-400:]}"
        )
        assert (
            "empty metadata values" in result.stdout
        ), f"failure must name empty evidence values, got: {result.stdout[-400:]}"

    def test_executed_bad_values_fail_evidence_contract(self) -> None:
        """Non-empty but malformed metadata (timestamp, SHAs) must fail.

        P1-2: validation goes beyond non-empty. The execution_timestamp must be
        ISO-8601 and the source/gitops SHAs must be real git SHAs or refs.
        """
        import subprocess
        import sys

        if not AUDIT_SCRIPT.exists():
            pytest.xfail("audit script not yet created")
        fixture = REPO_ROOT / "tests" / "phase2" / "fixtures" / "executed-bad-values-matrix.csv"
        assert fixture.exists(), f"fixture {fixture} not found"
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--require-executed",
                "--ml",
                "1",
                "--llm",
                "0",
                "--matrix",
                str(fixture),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1, (
            f"malformed evidence values must fail phase-08 audit, got {result.returncode}: "
            f"{result.stdout[-400:]}"
        )
        assert (
            "is not valid" in result.stdout and "execution_timestamp" in result.stdout
        ), f"failure must name malformed fields, got: {result.stdout[-400:]}"

    def test_executed_missing_artifact_fails(self) -> None:
        """An executed row whose implementation artifact is absent must fail.

        P1-1: executed evidence proves a running system. Even with a fully
        valid evidence file, a row whose artifact_path does not exist on disk
        cannot be promoted at phase-08.
        """
        import subprocess
        import sys

        if not AUDIT_SCRIPT.exists():
            pytest.xfail("audit script not yet created")
        fixture = (
            REPO_ROOT / "tests" / "phase2" / "fixtures" / "executed-missing-artifact-matrix.csv"
        )
        assert fixture.exists(), f"fixture {fixture} not found"
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--require-executed",
                "--ml",
                "1",
                "--llm",
                "0",
                "--matrix",
                str(fixture),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1, (
            f"missing artifact must fail phase-08 audit, got {result.returncode}: "
            f"{result.stdout[-400:]}"
        )
        assert (
            "implementation artifact not found" in result.stdout
        ), f"failure must name the missing artifact, got: {result.stdout[-400:]}"
