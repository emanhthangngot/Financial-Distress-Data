from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cluster_image_packages_existing_phase1_tree_without_protected_edits() -> None:
    dockerfile = REPO_ROOT / "infra/lakehouse-cluster/Dockerfile.pipeline"
    text = dockerfile.read_text(encoding="utf-8")
    assert "COPY src ./src" in text
    assert "COPY dags ./dags" in text
    assert "COPY configs ./configs" in text
    assert "ENTRYPOINT" in text
    assert "kubectl apply" not in text


def test_cluster_runtime_documentation_keeps_local_reproduction_path() -> None:
    readme = (REPO_ROOT / "infra/lakehouse-cluster/README.md").read_text(encoding="utf-8")
    assert "docker compose" in readme
    assert "quality gates" in readme
