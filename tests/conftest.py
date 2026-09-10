from __future__ import annotations

import pytest

from scripts.reconcile_test_scope import (
    DECOMMISSIONED_CLASSES,
    ENVIRONMENT_CLASSES,
    LEGACY_CLASSES,
    OBSOLETE_CLASSES,
    RESEARCH_CLASSES,
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Assign every collected test to one explicit primary execution scope.

    These markers change selection only when a certification command uses
    ``-m``.  A normal unfiltered pytest invocation remains unchanged.
    """
    for item in items:
        module_name = getattr(getattr(item, "module", None), "__name__", "")
        nodeid = item.nodeid.replace("\\", "/").lower()
        test_file = nodeid.split("::", 1)[0]
        junit_classname = test_file.removesuffix(".py").replace("/", ".")
        known_names = {module_name, junit_classname}
        if (
            known_names & ENVIRONMENT_CLASSES
            or "paper_natural_execution_e2e/" in nodeid
        ):
            item.add_marker(pytest.mark.environment_required)
        elif known_names & DECOMMISSIONED_CLASSES:
            item.add_marker(pytest.mark.decommissioned_feature)
        elif known_names & LEGACY_CLASSES or "trade_15m_v1" in nodeid:
            item.add_marker(pytest.mark.legacy_compat)
        elif known_names & OBSOLETE_CLASSES:
            item.add_marker(pytest.mark.obsolete_replaced)
        elif known_names & RESEARCH_CLASSES or "/research/" in nodeid:
            item.add_marker(pytest.mark.active_research)
        else:
            item.add_marker(pytest.mark.active_production)
