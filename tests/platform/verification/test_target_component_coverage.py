"""Target architecture component coverage (plan phase-03-contracts-rubric.md, Step 6).

Exercises scripts/verify_target_architecture.py's static structure — the
live-cluster probes themselves need a real kubectl context and are not
re-verified here (see the script's own docstring for that evidence).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location(
    "verify_target_architecture", REPO_ROOT / "scripts" / "verify_target_architecture.py"
)
_module = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["verify_target_architecture"] = _module
_spec.loader.exec_module(_module)


def test_eighty_three_components_declared() -> None:
    """AC-P3-6: one check per component/edge in the target image, 83 total."""
    assert len(_module.TARGET_COMPONENTS) == 83


def test_component_numbers_are_unique_and_sequential() -> None:
    numbers = sorted(c.number for c in _module.TARGET_COMPONENTS)
    assert numbers == list(range(1, 84))


def test_every_component_has_a_valid_owning_phase() -> None:
    for component in _module.TARGET_COMPONENTS:
        assert component.owning_phase.startswith("P")
        phase_num = int(component.owning_phase[1:])
        assert 2 <= phase_num <= 12, f"component {component.number} owning_phase out of range"


def test_every_change_class_is_one_of_the_declared_five_or_a_combination() -> None:
    """Class per plan §4.1: A restore, B bind, C build, D drift, E exists unchanged."""
    valid = {"A", "B", "C", "D", "E"}
    for component in _module.TARGET_COMPONENTS:
        classes = set(component.change_class.replace("+", ""))
        assert (
            classes <= valid
        ), f"component {component.number} has invalid class {component.change_class!r}"


def test_check_component_returns_false_without_a_namespace() -> None:
    """External actors / annotated edges with no namespace probe are never
    falsely reported as live — they fail closed."""
    external_actor = next(c for c in _module.TARGET_COMPONENTS if c.probe[1] is None)
    assert _module.check_component(external_actor) is False
