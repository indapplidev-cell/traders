from app.training.training_pipeline_runner import LongHistoryTrainingPipelineRunner


def test_ml38_10_14_2_training_runner_attaches_entry_path_profit_summary() -> None:
    runner = LongHistoryTrainingPipelineRunner()
    payload: dict[str, object] = {}

    runner._attach_profit_exit_root_cause_payload(
        payload,
        profit_aware_summary={
            "summary": {
                "entry_path_prediction_filter_summary": {
                    "blocked_prediction_rows": 3,
                    "stop_pressure_effectiveness_audit": {
                        "diagnostic_version": "ml38.10.14.2",
                        "status": "STOP_PRESSURE_REMOVED_FALSE_POSITIVES",
                    },
                },
                "stop_pressure_effectiveness_audit": {
                    "diagnostic_version": "ml38.10.14.2",
                    "status": "STOP_PRESSURE_REMOVED_FALSE_POSITIVES",
                },
            }
        },
    )

    assert payload["entry_path_prediction_filter_summary"]["blocked_prediction_rows"] == 3
    assert payload["stop_pressure_effectiveness_audit"]["status"] == "STOP_PRESSURE_REMOVED_FALSE_POSITIVES"
