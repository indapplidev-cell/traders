from app.db.models import MarketCandles, MlFeatures, MlLabels, MlModelVersions, MlReplayResults, MlReplaySessions, MlTrainingRuns


def test_db_models_expose_required_constraints_and_indexes() -> None:
    market_index_names = {index.name for index in MarketCandles.__table__.indexes}
    feature_index_names = {index.name for index in MlFeatures.__table__.indexes}
    label_index_names = {index.name for index in MlLabels.__table__.indexes}
    model_index_names = {index.name for index in MlModelVersions.__table__.indexes}
    replay_result_index_names = {index.name for index in MlReplayResults.__table__.indexes}

    assert "ix_market_candles_symbol_interval_open_time" in market_index_names
    assert "ix_ml_features_symbol_interval_cot_fv" in feature_index_names
    assert "ix_ml_labels_symbol_interval_cot_hc_lv" in label_index_names
    assert "ix_ml_model_versions_symbol_interval_horizon_active" in model_index_names
    assert "uq_ml_model_versions_active_scope" in model_index_names
    assert "ix_ml_replay_results_session_id" in replay_result_index_names

    model_unique_names = {constraint.name for constraint in MlModelVersions.__table__.constraints if getattr(constraint, "name", None)}
    training_unique_names = {constraint.name for constraint in MlTrainingRuns.__table__.constraints if getattr(constraint, "name", None)}
    replay_session_unique_names = {constraint.name for constraint in MlReplaySessions.__table__.constraints if getattr(constraint, "name", None)}

    assert "uq_ml_model_versions_model_version" in model_unique_names
    assert "uq_ml_training_runs_run_id" in training_unique_names
    assert "uq_ml_replay_sessions_session_id" in replay_session_unique_names
