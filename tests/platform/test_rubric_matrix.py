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
    "sql/",
    "docs/01_data_generator.md",
    "docs/architecture/data-model.md",
    "docs/evidence/",
    "docs/mini_coursework.md",
    "tests/test_lakehouse",
]

# ── Phase 2 evidence_audit script ───────────────────────────────────────
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_platform_evidence.py"


class TestPhase1ContractNoMutation:
    """Phase 1 must not be mutated by Phase 2 matrix or linter."""

    def test_audit_script_exists(self) -> None:
        """audit_platform_evidence.py must exist before Phase 2 gates can run."""
        assert (
            AUDIT_SCRIPT.exists()
        ), f"{AUDIT_SCRIPT} missing — create scripts/audit_platform_evidence.py"

    def test_no_protected_paths_in_matrix(self) -> None:
        """Matrix MUST NOT claim to modify Phase 1 protected paths."""
        if not MATRIX_CSV.exists():
            pytest.fail(f"{MATRIX_CSV} missing — run 'scripts/_platform_rubric_items.py' first")
        text = MATRIX_CSV.read_text(encoding="utf-8").lower()
        for path in PHASE1_PROTECTED:
            if path.lower() in text:
                pytest.fail(
                    f"Matrix references Phase 1 protected path '{path}' — "
                    "Phase 2 must not mutate Phase 1."
                )
        assert "dags/" in text, "Phase 2 Airflow wrappers must be mapped explicitly"

    def test_phase1_mutation_from_changed_paths(self) -> None:
        """A git diff that touches a Phase 1 path must be flagged."""
        import importlib.util

        if not AUDIT_SCRIPT.exists():
            pytest.fail("audit script missing")
        spec = importlib.util.spec_from_file_location("audit_platform", AUDIT_SCRIPT)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # A diff touching a collector must fail
        errors = mod._phase1_mutation_from_changed(["src/collectors/some_adapter.py"])
        assert any("src/collectors/" in e for e in errors)

        # A diff touching only Phase 2 files must pass
        ok = mod._phase1_mutation_from_changed(
            [
                "docs/phase2/architecture.md",
                "scripts/audit_platform_evidence.py",
                "dags/drift_monitoring.py",
            ]
        )
        assert ok == [], f"expected no Phase 1 mutation, got {ok}"
        dag_errors = mod._phase1_mutation_from_changed(["dags/01_collect_company_master_data.py"])
        assert dag_errors, "an existing Phase 1 DAG change must fail"

        # A diff confined to the opt-in Flink job home carve-out must pass:
        # it holds no Phase 1 burst/late-arrival/dedup logic by design.
        flink_ok = mod._phase1_mutation_from_changed(
            [
                "src/streaming/flink/jobs/price_event_job.py",
                "src/streaming/flink/jobs/README.md",
            ]
        )
        assert flink_ok == [], f"expected no Phase 1 mutation, got {flink_ok}"

        # But any other file directly under src/streaming/ must still fail.
        streaming_errors = mod._phase1_mutation_from_changed(
            ["src/streaming/kafka_to_bronze_consumer.py"]
        )
        assert streaming_errors, "a core streaming file change must still fail"


class TestRubricMatrix:
    """Validate rubric matrix completeness and invariants."""

    def test_matrix_csv_exists(self) -> None:
        """rubric-matrix.csv must exist."""
        assert (
            MATRIX_CSV.exists()
        ), f"{MATRIX_CSV} not found — create it via scripts/_platform_rubric_items.py"

    def test_matrix_csv_matches_generator_exactly(self) -> None:
        """The committed export must not drift from canonical generation."""
        import sys

        sys.path.insert(0, str(REPO_ROOT))
        from scripts._platform_rubric_items import export_matrix_csv

        assert MATRIX_CSV.read_text(encoding="utf-8") == export_matrix_csv()

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
        deliverables, owner, mapping test, behavior validation, source
        provenance, acceptance ID, evidence and exact artifact reference."""
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
            "validation_command",
            "evidence_path",
            "evidence_type",
            "acceptance_id",
            "source_file",
            "source_row_index",
            "source_digest",
            "artifact_repo",
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

    def test_no_rubric_id_is_a_prefix_of_another(self) -> None:
        """No rubric_id may be a substring of another's.

        `validation_command` selects rows with `pytest -k '<rubric_id>'`,
        which is a substring match, not an exact/anchored one. If one row's id
        is a prefix of another's (e.g. a blind `-1` dedup suffix on an
        otherwise-identical slug), `-k` selects both and phase-08's
        `_audit_behavior_validations` mis-attributes one row's failure to the
        other. Caught 2026-08-07 for two such pairs; see
        `_COLLISION_RENAMES` in scripts/_platform_rubric_items.py for the fix.
        """
        import csv
        import io

        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        ids = [row["rubric_id"] for row in reader]
        collisions = [(a, b) for a in ids for b in ids if a != b and b.startswith(a)]
        assert not collisions, f"rubric_id prefix collisions (breaks -k selection): {collisions}"

    def test_contract_and_behavior_commands_are_distinct(self) -> None:
        """Every row separates mapping checks from feature behavior proof."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        bad: list[str] = []
        for row in reader:
            test = row.get("test", "")
            if not test.startswith("pytest tests/platform"):
                bad.append(f"{row.get('rubric_id','?')}: test='{test}' not reproducible")
            validation = row.get("validation_command", "")
            if not re.fullmatch(
                r"pytest tests/platform/requirements/test_[a-z0-9_]+\.py -k '[A-Za-z0-9-]+'",
                validation,
            ):
                bad.append(f"{row.get('rubric_id','?')}: validation_command='{validation}' invalid")
            if validation == test:
                bad.append(f"{row.get('rubric_id','?')}: behavior gate equals metadata test")
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

    def test_artifact_paths_are_concrete_and_repo_qualified(self) -> None:
        """Every row must name a concrete file in source or GitOps."""
        import csv
        import io

        if not MATRIX_CSV.exists():
            pytest.xfail("Matrix CSV not yet created")
        roots = {
            "source": (
                "src/ml/",
                "src/drift/",
                "src/llm/",
                "src/agents/",
                "apps/",
                "dags/",
                ".github/workflows/",
                "notebooks/",
                "tests/platform/requirements/",
                "docs/phase2/",
            ),
            "gitops": (
                ".github/workflows/",
                "terraform/",
                "ansible/",
                "charts/",
                "platform/",
                "argocd/",
            ),
        }
        reader = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        used_repos: set[str] = set()
        for row in reader:
            rid = row.get("rubric_id", "?")
            repo = row.get("artifact_repo", "")
            apath = row.get("artifact_path", "")
            assert repo in roots, f"{rid}: artifact_repo={repo!r} invalid"
            assert apath, f"{rid}: missing artifact_path (exact implementation)"
            assert apath.startswith(
                roots[repo]
            ), f"{rid}: artifact_path='{apath}' not valid for repo '{repo}'"
            assert not apath.endswith("/"), f"{rid}: artifact_path must name a file"
            assert Path(apath).suffix, f"{rid}: artifact_path lacks a file suffix"
            used_repos.add(repo)
        assert used_repos == {"source", "gitops"}

    def test_canonical_source_coverage_rejects_point_transfer(self) -> None:
        """Deleting a row and moving its points cannot preserve a passing audit."""
        import csv
        import importlib.util
        import io

        spec = importlib.util.spec_from_file_location("audit_platform", AUDIT_SCRIPT)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows = list(csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8"))))
        removed = rows.pop(0)
        replacement = next(row for row in rows if row["track"] == removed["track"])
        replacement["points"] = str(int(replacement["points"]) + int(removed["points"]))
        errors = mod._audit_canonical_coverage(rows)
        assert errors and "canonical source coverage" in errors[0]

    def test_canonical_source_coverage_rejects_digest_tamper(self) -> None:
        import csv
        import importlib.util
        import io

        spec = importlib.util.spec_from_file_location("audit_platform_digest", AUDIT_SCRIPT)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows = list(csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8"))))
        rows[0]["source_digest"] = "0" * 64
        assert mod._audit_canonical_coverage(rows)

    def test_promotion_rejects_explicit_artifact_map_tamper(self) -> None:
        """A valid-looking path cannot replace the reviewed row mapping."""
        import csv
        import importlib.util
        import io

        spec = importlib.util.spec_from_file_location("audit_platform_map", AUDIT_SCRIPT)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows = list(csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8"))))
        rows[0]["artifact_path"] = "docs/phase2/requirements.md"
        errors = mod._audit_matrix(
            rows,
            {"ML": 100, "LLM": 100},
            enforce_explicit_implementation=True,
        )
        assert any("implementation mapping diverges" in error for error in errors)


class TestAcceptanceCriteria:
    """AC must be in WHO -> ACTION -> RESULT format."""

    def test_acceptance_criteria_doc_exists(self) -> None:
        """The resolvable acceptance catalog must exist."""
        reqs_md = REPO_ROOT / "docs" / "phase2" / "acceptance-criteria.md"
        assert reqs_md.exists(), (
            f"{reqs_md} not found — write per-deliverable AA in" " WHO -> ACTION -> RESULT form"
        )

    def test_acceptance_criteria_in_who_action_result(self) -> None:
        """At least one acceptance criterion follows WHO -> ACTION -> RESULT pattern."""
        reqs_md = REPO_ROOT / "docs" / "phase2" / "acceptance-criteria.md"
        if not reqs_md.exists():
            pytest.xfail("requirements.md not yet created")
        text = reqs_md.read_text(encoding="utf-8")
        # WHO → ACTION → RESULT detection: a line with two arrows
        found = re.search(r"\s*->\s*.+->\s*.+", text)
        assert found, (
            "No WHO -> ACTION -> RESULT acceptance criterion found in "
            "docs/phase2/acceptance-criteria.md"
        )

    def test_every_matrix_acceptance_id_resolves(self) -> None:
        import csv
        import io

        catalog = (REPO_ROOT / "docs/phase2/acceptance-criteria.md").read_text(encoding="utf-8")
        declared = set(re.findall(r"`((?:ML|LLM)-AC-[A-Z0-9-]+)`", catalog))
        rows = csv.DictReader(io.StringIO(MATRIX_CSV.read_text(encoding="utf-8")))
        unresolved = [row["rubric_id"] for row in rows if row["acceptance_id"] not in declared]
        assert not unresolved, f"unresolved acceptance IDs for {unresolved}"


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

    def test_platform_architecture_doc_exists(self) -> None:
        path = REPO_ROOT / "docs" / "phase2" / "architecture.md"
        assert path.exists(), f"{path} not found"

    def test_nine_adrs_exist(self) -> None:
        adr_dir = REPO_ROOT / "docs" / "phase2" / "adr"
        if not adr_dir.exists():
            pytest.fail(f"ADR dir {adr_dir} not found")
        adrs = list(adr_dir.glob("adr-*.md"))
        assert len(adrs) >= 9, f"Expected ≥ 9 ADRs, found {len(adrs)}"

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

    def test_behavior_validation_mode_requires_executed_gate(self) -> None:
        """Feature commands cannot be run outside the Phase 8 evidence gate."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT), "--run-validations"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1
        assert "requires --require-executed" in result.stdout

    def test_track_filter_scopes_executed_gate_to_llm(self) -> None:
        """`--track LLM` must report zero ML-prefixed findings under --require-executed."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT), "--require-executed", "--track", "LLM"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        ml_findings = [line for line in result.stdout.splitlines() if re.match(r"^ML-", line)]
        assert not ml_findings, f"--track LLM must not scope ML rows, found: {ml_findings[:5]}"

    def test_track_never_scopes_canonical_coverage(self) -> None:
        """`--track LLM` on --matrix-only must not shrink the 117-row requirement.

        Pins the unfiltered call sites (_audit_matrix, _audit_canonical_coverage)
        for real: passing --track here would still have to fail if either one
        started consuming the scoped list instead of the full matrix.
        """
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT), "--matrix-only", "--strict", "--track", "LLM"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            "matrix-only gate must still require all 117 canonical rows even "
            f"with --track LLM passed: {result.stdout[-400:]}"
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
        fixture = REPO_ROOT / "tests" / "platform" / "fixtures" / "incomplete-matrix.csv"
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
        fixture = REPO_ROOT / "tests" / "platform" / "fixtures" / "design-only-matrix.csv"
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
        fixture = REPO_ROOT / "tests" / "platform" / "fixtures" / "executed-incomplete-matrix.csv"
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
        fixture = REPO_ROOT / "tests" / "platform" / "fixtures" / "executed-empty-values-matrix.csv"
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
        fixture = REPO_ROOT / "tests" / "platform" / "fixtures" / "executed-bad-values-matrix.csv"
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
            REPO_ROOT / "tests" / "platform" / "fixtures" / "executed-missing-artifact-matrix.csv"
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


class TestPhase2PromotionHardening:
    """Adversarial regression tests for generated artifacts and promotion gates."""

    @staticmethod
    def _load_module(path: Path, name: str):
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _git(root: Path, *args: str) -> str:
        import subprocess

        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    @classmethod
    def _commit(cls, root: Path, message: str) -> str:
        cls._git(root, "add", ".")
        cls._git(
            root,
            "-c",
            "user.name=phase2-test",
            "-c",
            "user.email=phase2-test@example.invalid",
            "commit",
            "-m",
            message,
        )
        return cls._git(root, "rev-parse", "HEAD")

    @pytest.mark.parametrize(
        "body",
        [
            "def behavior():\n    ...\n",
            "def behavior():\n    raise NotImplementedError\n",
            "def behavior():\n    raise NotImplementedError('TODO')\n",
        ],
    )
    def test_python_symbol_rejects_placeholder_bodies(self, tmp_path: Path, body: str) -> None:
        helper = self._load_module(
            REPO_ROOT / "tests/platform/requirements/conftest.py",
            "phase2_generated_contract_helper",
        )
        artifact = tmp_path / "behavior.py"
        artifact.write_text(body, encoding="utf-8")
        with pytest.raises(AssertionError, match="placeholder"):
            helper.assert_behavioral_contract(artifact, "python_ast_symbol:behavior")

    @pytest.mark.parametrize(
        ("content", "assertion"),
        [
            ("placeholder: true\n", "yaml_mapping_contains:placeholder"),
            ("jobs:\n  test:\n    placeholder: true\n", "yaml_path:jobs.test"),
            ("# reserved\nTODO service\n", "text_contains:service"),
            (
                '{"cells":[{"cell_type":"code","source":["..."]}]}',
                "notebook_code_contains:cells",
            ),
        ],
    )
    def test_generated_contract_rejects_placeholder_artifacts(
        self, tmp_path: Path, content: str, assertion: str
    ) -> None:
        helper = self._load_module(
            REPO_ROOT / "tests/platform/requirements/conftest.py",
            "phase2_generated_placeholder_helper",
        )
        suffix = ".ipynb" if assertion.startswith("notebook") else ".yaml"
        artifact = tmp_path / f"artifact{suffix}"
        artifact.write_text(content, encoding="utf-8")
        with pytest.raises(AssertionError):
            helper.assert_behavioral_contract(artifact, assertion)

    def test_generic_python_requires_behavior_beyond_imports(self, tmp_path: Path) -> None:
        helper = self._load_module(
            REPO_ROOT / "tests/platform/requirements/conftest.py",
            "phase2_generated_python_helper",
        )
        artifact = tmp_path / "service.py"
        artifact.write_text('"""service"""\nimport os\n', encoding="utf-8")
        with pytest.raises(AssertionError, match="no executable"):
            helper.assert_behavioral_contract(artifact, "python_ast_contains:service")

    @pytest.mark.parametrize(
        "method_body",
        ["...", "pass", '"""future"""', "raise NotImplementedError"],
    )
    def test_python_class_symbol_rejects_placeholder_methods(
        self, tmp_path: Path, method_body: str
    ) -> None:
        helper = self._load_module(
            REPO_ROOT / "tests/platform/requirements/conftest.py",
            "phase2_generated_class_helper",
        )
        artifact = tmp_path / "service.py"
        artifact.write_text(
            "class Service:\n"
            "    ACTIVE = True\n"
            "    def run(self):\n"
            f"        {method_body}\n",
            encoding="utf-8",
        )
        with pytest.raises(AssertionError, match="Service.run is a placeholder"):
            helper.assert_behavioral_contract(artifact, "python_ast_symbol:Service")

    def test_generic_python_rejects_metadata_only_assignment(self, tmp_path: Path) -> None:
        helper = self._load_module(
            REPO_ROOT / "tests/platform/requirements/conftest.py",
            "phase2_generated_assignment_helper",
        )
        artifact = tmp_path / "service.py"
        artifact.write_text("SERVICE = None\n", encoding="utf-8")
        with pytest.raises(AssertionError, match="no executable"):
            helper.assert_behavioral_contract(artifact, "python_ast_contains:service")

    def test_generic_yaml_rejects_metadata_only_configmap(self, tmp_path: Path) -> None:
        helper = self._load_module(
            REPO_ROOT / "tests/platform/requirements/conftest.py",
            "phase2_generated_configmap_helper",
        )
        artifact = tmp_path / "service.yaml"
        artifact.write_text(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: service\n",
            encoding="utf-8",
        )
        with pytest.raises(AssertionError, match="metadata only"):
            helper.assert_behavioral_contract(artifact, "yaml_mapping_contains:service")

    def test_generic_text_rejects_one_token_skeleton(self, tmp_path: Path) -> None:
        helper = self._load_module(
            REPO_ROOT / "tests/platform/requirements/conftest.py",
            "phase2_generated_text_helper",
        )
        artifact = tmp_path / "service.md"
        artifact.write_text("service\n", encoding="utf-8")
        with pytest.raises(AssertionError, match="path/token skeleton"):
            helper.assert_behavioral_contract(artifact, "text_contains:service")

    def test_executed_row_requires_explicit_behavioral_override(self) -> None:
        rubric = self._load_module(
            REPO_ROOT / "scripts/_platform_rubric_items.py",
            "phase2_rubric_executed_assertion",
        )
        row = {
            "rubric_id": "LLM-unreviewed-executed-row",
            "evidence_type": "executed",
            "behavioral_assertion": "python_ast_contains:service",
        }
        with pytest.raises(ValueError, match="no explicit row-specific"):
            rubric._validate_executed_behavioral_assertion(row)

    def test_ancestor_sha_allows_only_evidence_sha_delta(self, tmp_path: Path) -> None:
        audit = self._load_module(AUDIT_SCRIPT, "phase2_audit_ancestor")
        self._git(tmp_path, "init", "-b", "main")
        evidence = tmp_path / "docs/phase2/evidence/llm/row.md"
        evidence.parent.mkdir(parents=True)
        evidence.write_text("- source_sha: old\n", encoding="utf-8")
        (tmp_path / "implementation.py").write_text("VALUE = 1\n", encoding="utf-8")
        implementation_sha = self._commit(tmp_path, "implementation")
        evidence.write_text("- source_sha: stamped\n", encoding="utf-8")
        stamped_sha = self._commit(tmp_path, "stamp sha")

        assert audit._revision_is_ancestor(tmp_path, implementation_sha, stamped_sha)
        assert audit._only_evidence_sha_lines_changed(tmp_path, implementation_sha, stamped_sha)

        evidence.write_text(
            "- source_sha: stamped\n- actual_result: changed after execution\n",
            encoding="utf-8",
        )
        non_sha_evidence_change = self._commit(tmp_path, "change evidence result")
        assert not audit._only_evidence_sha_lines_changed(
            tmp_path, implementation_sha, non_sha_evidence_change
        )

        (tmp_path / "implementation.py").write_text("VALUE = 2\n", encoding="utf-8")
        tampered_sha = self._commit(tmp_path, "tamper implementation")
        assert not audit._only_evidence_sha_lines_changed(
            tmp_path, implementation_sha, tampered_sha
        )

    def test_nonancestor_sha_is_rejected(self, tmp_path: Path) -> None:
        audit = self._load_module(AUDIT_SCRIPT, "phase2_audit_nonancestor")
        self._git(tmp_path, "init", "-b", "main")
        (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
        base_sha = self._commit(tmp_path, "base")
        self._git(tmp_path, "switch", "-c", "alternate")
        (tmp_path / "alternate.txt").write_text("alternate\n", encoding="utf-8")
        alternate_sha = self._commit(tmp_path, "alternate")
        self._git(tmp_path, "switch", "main")
        (tmp_path / "main.txt").write_text("main\n", encoding="utf-8")
        main_sha = self._commit(tmp_path, "main")

        assert audit._revision_is_ancestor(tmp_path, base_sha, main_sha)
        assert not audit._revision_is_ancestor(tmp_path, alternate_sha, main_sha)

    @pytest.mark.parametrize(
        ("body", "finding"),
        [
            ("ghp_" + "a" * 36, "GitHub token"),
            ("- Authorization: Bearer fake", "authorization header"),
            ("ssh -i key evidence-user@host", "SSH username"),
        ],
    )
    def test_secret_denylist_rejects_adversarial_forms(self, body: str, finding: str) -> None:
        audit = self._load_module(AUDIT_SCRIPT, "phase2_audit_secrets")
        errors = audit._audit_evidence_secrets("row", "row.md", body)
        assert any(finding in error for error in errors)

    def test_accept_design_only_rejects_non_design_rows(self) -> None:
        audit = self._load_module(AUDIT_SCRIPT, "phase2_audit_cuts")
        for evidence_type in ("executed", "stretch", "invalid"):
            row = {"rubric_id": "row", "evidence_type": evidence_type}
            errors = audit._audit_executed([row], None, {"row"})
            if evidence_type == "executed":
                assert errors and "no evidence_path" in errors[0]
            else:
                assert errors and "cannot accept" in errors[0]

    def test_interim_pending_audit_does_not_require_documented_final_cuts(self) -> None:
        import csv
        import os
        import subprocess
        import sys

        rows = list(csv.DictReader(MATRIX_CSV.read_text(encoding="utf-8").splitlines()))
        pending = [
            row["rubric_id"]
            for row in rows
            if row["track"] == "LLM" and row["evidence_type"] == "design_only"
        ]
        gitops_root = os.environ.get("PHASE2_GITOPS_ROOT")
        args = [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--strict",
            "--require-executed",
            "--track",
            "LLM",
            "--accept-design-only",
            ",".join(pending),
        ]
        if gitops_root:
            args += ["--gitops-root", gitops_root]
        result = subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if gitops_root is None:
            pytest.skip(
                "PHASE2_GITOPS_ROOT unset; the matrix has at least one executed "
                "gitops-artifact row and its behavioral validation needs a "
                "checked-out GitOps repo"
            )
        assert result.returncode == 0, result.stdout[-2000:]
        assert "pending interim row" in result.stdout
        assert "accepted final cut" not in result.stdout

    def test_final_promotion_requires_documented_cuts_and_frozen_base(self) -> None:
        import subprocess
        import sys

        # All real final cuts are documented in the submission README. Use a
        # synthetic ID here so this test exercises the undocumented-cut guard
        # without depending on a currently unclaimed rubric row.
        pending = "LLM-test-undocumented-cut"
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--strict",
                "--require-executed",
                "--track",
                "LLM",
                "--phase1-base",
                "0" * 40,
                "--accept-design-only",
                pending,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 1
        assert "final --accept-design-only cuts must be documented" in result.stdout
