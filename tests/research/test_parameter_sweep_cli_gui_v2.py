from traders_ml.parameter_sweep.cli import build_parser
from traders_ml.parameter_sweep.controller import PresentationState
from traders_ml.parameter_sweep.modes import RESEARCH_MODE_VALUES


def test_cli_exposes_stage_status_resume_and_migration_controls():
    parser = build_parser()
    assert parser.parse_args(["--mode", "ONE_FACTOR_SENSITIVITY"]).mode == "ONE_FACTOR_SENSITIVITY"
    assert parser.parse_args([]).mode == "ALL"
    assert tuple(next(a for a in parser._actions if a.dest == "mode").choices) == RESEARCH_MODE_VALUES
    args = parser.parse_args(["--migrate-v1", "old", "--migration-target", "new", "--dry-run"])
    assert args.dry_run and str(args.migrate_v1) == "old" and str(args.migration_target) == "new"


def test_gui_state_exposes_stage_family_classes_and_size_budget():
    state = PresentationState(current_stage="SMALL_FAMILY_SEARCH", current_parameter_family="GEOMETRY", artifact_bytes=1024, artifact_soft_budget_bytes=2048, artifact_hard_budget_bytes=4096, negative_expectancy=2, promising=1, validation_candidates=1)
    assert state.current_stage == "SMALL_FAMILY_SEARCH"
    assert state.current_parameter_family == "GEOMETRY"
    assert state.artifact_bytes < state.artifact_hard_budget_bytes
