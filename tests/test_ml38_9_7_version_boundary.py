from app import __version__
from app.config.settings import Settings
from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner


def test_project_version_bumped_to_0_2_0() -> None:
    assert __version__ == "0.2.0"
    assert Settings().service_version == "0.2.0"
    assert LongHistoryTrainingPipelineRunner._build_health_payload()["version"] == "0.2.0"

