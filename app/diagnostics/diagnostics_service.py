from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Iterable, Sequence

from app.baseline.baseline_by_regime_evaluator import BaselineByRegimeEvaluator
from app.baseline.directional_baseline_evaluator import DirectionalBaselineEvaluator
from app.baseline.baseline_service import BaselineService
from app.config.settings import PROJECT_ROOT
from app.dataset.dataset_builder import DatasetBuilder
from app.diagnostics.label_diagnostics import LabelDiagnostics
from app.diagnostics.meta_label_diagnostics import MetaLabelDiagnostics
from app.diagnostics.regime_segment_diagnostics import RegimeSegmentDiagnostics
from app.db.repositories.feature_repository import FeatureRepository
from app.diagnostics.dataset_diagnostics import DatasetDiagnostics
from app.diagnostics.directional_opportunity_diagnostics import DirectionalOpportunityDiagnostics
from app.diagnostics.entry_path_quality_filter import EntryPathQualityFilter
from app.diagnostics.feature_diagnostics_v2 import FeatureDiagnosticsV2
from app.diagnostics.fold_label_diagnostics import FoldLabelDiagnostics
from app.diagnostics.calibrated_prediction_decisions import CalibratedPredictionDecisions
from app.diagnostics.decision_policy_grid import DecisionPolicyGrid
from app.diagnostics.book_driven_forensic_audit import BookDrivenForensicAudit
from app.diagnostics.schwager_robustness_decision_board import build_schwager_slice_robustness
from app.diagnostics.prediction_collapse_detector import PredictionCollapseDetector
from app.diagnostics.prediction_bias_root_cause import PredictionBiasRootCause
from app.diagnostics.prediction_diagnostics import PredictionDiagnostics
from app.diagnostics.prediction_root_cause_audit import PredictionRootCauseAuditor
from app.diagnostics.prediction_probability_diagnostics import PredictionProbabilityDiagnostics
from app.evaluation.calibration_evaluator import CalibrationEvaluator
from app.evaluation.confidence_gate_evaluator import ConfidenceGateEvaluator
from app.evaluation.model_vs_baseline_comparator import ModelVsBaselineComparator
from app.evaluation.profit_aware_evaluator import ProfitAwareEvaluator
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.evaluation.signal_gate_evaluator import SignalGateEvaluator
from app.features.feature_models import feature_names_for_version
from app.models.model_factory import ModelFactory
from app.meta_label.ema_meta_label_builder import EmaMetaLabelBuilder
from app.meta_label.meta_baseline_evaluator import MetaBaselineEvaluator
from app.meta_label.meta_dataset_builder import MetaDatasetBuilder
from app.meta_label.meta_label_models import (
    EMA_DIRECTION_LONG,
    EMA_DIRECTION_SHORT,
    MetaDatasetRow,
    MetaLabelRecord,
)
from app.meta_label.meta_training_service import MetaTrainingService
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_loader import ModelLoader
from app.training.loss import MultiTaskLoss
from app.training.probability_calibration import direction_temperature_from_metadata, softmax_with_temperature
from app.training.trainer import Trainer
from app.training.training_service import TrainingService
from app.validation.walk_forward_evaluator import WalkForwardEvaluator
from app.validation.walk_forward_splitter import WalkForwardConfig, WalkForwardSplitter


class DiagnosticsService:
    def __init__(
        self,
        dataset_builder: DatasetBuilder,
        feature_repository: FeatureRepository,
        model_registry_repository,
        artifact_storage: ArtifactStorage,
        candle_repository=None,
        label_repository=None,
        reports_dir: Path | None = None,
        dataset_diagnostics: DatasetDiagnostics | None = None,
        prediction_diagnostics: PredictionDiagnostics | None = None,
        label_diagnostics: LabelDiagnostics | None = None,
        prediction_probability_diagnostics: PredictionProbabilityDiagnostics | None = None,
        prediction_collapse_detector: PredictionCollapseDetector | None = None,
        model_loader: ModelLoader | None = None,
        model_factory: ModelFactory | None = None,
        confidence_gate_evaluator: ConfidenceGateEvaluator | None = None,
        profit_aware_evaluator: ProfitAwareEvaluator | None = None,
        calibration_evaluator: CalibrationEvaluator | None = None,
        signal_gate_evaluator: SignalGateEvaluator | None = None,
        profit_aware_evaluator_v2: ProfitAwareEvaluatorV2 | None = None,
        walk_forward_splitter: WalkForwardSplitter | None = None,
        walk_forward_evaluator: WalkForwardEvaluator | None = None,
        directional_baseline_evaluator: DirectionalBaselineEvaluator | None = None,
        fold_label_diagnostics: FoldLabelDiagnostics | None = None,
        directional_opportunity_diagnostics: DirectionalOpportunityDiagnostics | None = None,
        prediction_bias_root_cause: PredictionBiasRootCause | None = None,
        feature_diagnostics_v2: FeatureDiagnosticsV2 | None = None,
        model_vs_baseline_comparator: ModelVsBaselineComparator | None = None,
        regime_segment_diagnostics: RegimeSegmentDiagnostics | None = None,
        baseline_by_regime_evaluator: BaselineByRegimeEvaluator | None = None,
        ema_meta_label_builder: EmaMetaLabelBuilder | None = None,
        meta_label_diagnostics: MetaLabelDiagnostics | None = None,
        meta_dataset_builder: MetaDatasetBuilder | None = None,
        meta_baseline_evaluator: MetaBaselineEvaluator | None = None,
        meta_training_service: MetaTrainingService | None = None,
    ) -> None:
        self._dataset_builder = dataset_builder
        self._feature_repository = feature_repository
        self._model_registry_repository = model_registry_repository
        self._artifact_storage = artifact_storage
        self._candle_repository = candle_repository
        self._label_repository = label_repository
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._dataset_diagnostics = dataset_diagnostics or DatasetDiagnostics()
        self._prediction_diagnostics = prediction_diagnostics or PredictionDiagnostics()
        self._label_diagnostics = label_diagnostics or LabelDiagnostics()
        self._prediction_probability_diagnostics = prediction_probability_diagnostics or PredictionProbabilityDiagnostics()
        self._prediction_collapse_detector = prediction_collapse_detector or PredictionCollapseDetector()
        self._calibrated_prediction_decisions = CalibratedPredictionDecisions()
        self._decision_policy_grid = DecisionPolicyGrid()
        self._entry_path_quality_filter = EntryPathQualityFilter()
        self._model_loader = model_loader or ModelLoader(artifact_storage=self._artifact_storage)
        self._model_factory = model_factory or ModelFactory()
        self._confidence_gate_evaluator = confidence_gate_evaluator or ConfidenceGateEvaluator(reports_dir=self._reports_dir)
        self._profit_aware_evaluator = profit_aware_evaluator or ProfitAwareEvaluator(reports_dir=self._reports_dir)
        self._calibration_evaluator = calibration_evaluator or CalibrationEvaluator(reports_dir=self._reports_dir)
        self._signal_gate_evaluator = signal_gate_evaluator or SignalGateEvaluator(reports_dir=self._reports_dir)
        self._profit_aware_evaluator_v2 = profit_aware_evaluator_v2 or ProfitAwareEvaluatorV2(
            reports_dir=self._reports_dir,
            signal_gate_evaluator=self._signal_gate_evaluator,
        )
        self._walk_forward_splitter = walk_forward_splitter or WalkForwardSplitter()
        self._walk_forward_evaluator = walk_forward_evaluator or WalkForwardEvaluator(
            reports_dir=self._reports_dir,
            walk_forward_splitter=self._walk_forward_splitter,
            profit_evaluator_v2=self._profit_aware_evaluator_v2,
        )
        self._directional_baseline_evaluator = directional_baseline_evaluator or DirectionalBaselineEvaluator(
            reports_dir=self._reports_dir,
            walk_forward_splitter=self._walk_forward_splitter,
            profit_evaluator_v2=self._profit_aware_evaluator_v2,
        )
        self._fold_label_diagnostics = fold_label_diagnostics or FoldLabelDiagnostics()
        self._directional_opportunity_diagnostics = (
            directional_opportunity_diagnostics or DirectionalOpportunityDiagnostics()
        )
        self._prediction_bias_root_cause = prediction_bias_root_cause or PredictionBiasRootCause()
        self._feature_diagnostics_v2 = feature_diagnostics_v2 or FeatureDiagnosticsV2()
        self._model_vs_baseline_comparator = model_vs_baseline_comparator or ModelVsBaselineComparator()
        self._regime_segment_diagnostics = regime_segment_diagnostics or RegimeSegmentDiagnostics()
        self._baseline_by_regime_evaluator = baseline_by_regime_evaluator or BaselineByRegimeEvaluator(
            reports_dir=self._reports_dir,
            walk_forward_splitter=self._walk_forward_splitter,
            profit_evaluator_v2=self._profit_aware_evaluator_v2,
        )
        self._ema_meta_label_builder = ema_meta_label_builder or EmaMetaLabelBuilder()
        self._meta_label_diagnostics = meta_label_diagnostics or MetaLabelDiagnostics()
        self._meta_dataset_builder = meta_dataset_builder or MetaDatasetBuilder()
        self._meta_baseline_evaluator = meta_baseline_evaluator or MetaBaselineEvaluator(
            reports_dir=self._reports_dir,
            walk_forward_splitter=self._walk_forward_splitter,
        )
        self._meta_training_service = meta_training_service or MetaTrainingService(
            artifact_storage=self._artifact_storage,
            model_factory=self._model_factory,
            model_loader=self._model_loader,
        )

    def dataset_report(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
    ) -> dict[str, Any]:
        dataset_rows, summary = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        split_rows = self._dataset_builder.split_rows(dataset_rows, train_end=train_end, validation_end=validation_end)
        raw_feature_rows = self._feature_repository.get_all(symbol=symbol, interval=interval, feature_version=feature_version)
        report = {
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "feature_version": feature_version,
            "label_version": label_version,
            "train_end": train_end.isoformat() if train_end is not None else None,
            "validation_end": validation_end.isoformat() if validation_end is not None else None,
            "dataset_summary": summary,
            **self._dataset_diagnostics.build_report(dataset_rows, split_rows, raw_feature_rows),
        }
        output_path = self._reports_dir / f"dataset_diagnostics_{symbol.lower()}_{interval}_h{horizon_candles}_{feature_version}_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def label_report(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        label_version: str,
    ) -> dict[str, Any]:
        if self._label_repository is None:
            raise ValueError("Label repository is required for label diagnostics.")
        labels = self._label_repository.get_all(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version=label_version,
        )
        report = self._label_diagnostics.build_report(
            labels=labels,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version=label_version,
        )
        output_path = self._reports_dir / f"label_diagnostics_{symbol.lower()}_{interval}_h{horizon_candles}_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def model_report(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
        start_at=None,
        end_at=None,
    ) -> dict[str, Any]:
        model_row = self._model_registry_repository.get_by_model_version(model_version)
        if model_row is None:
            raise ValueError(f"Unknown model_version: {model_version}")

        model, scaler, feature_columns, _, _ = self._model_loader.load(model_version)
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            start_at=start_at,
            end_at=end_at,
        )
        split_rows = self._dataset_builder.split_rows(dataset_rows, train_end=train_end, validation_end=validation_end)
        split_reports = {
            split_name: self._prediction_diagnostics.analyze_split(model, rows, feature_columns, scaler)
            for split_name, rows in split_rows.items()
        }
        collapse_detected, collapse_reason = self._detect_collapse(split_reports["test"]["predicted_counts"], split_reports["test"]["rows"])
        report = {
            "model_version": model_version,
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "feature_version": feature_version,
            "label_version": label_version,
            "train_end": train_end.isoformat() if train_end is not None else None,
            "validation_end": validation_end.isoformat() if validation_end is not None else None,
            "actual_counts_train": split_reports["train"]["actual_counts"],
            "actual_counts_validation": split_reports["validation"]["actual_counts"],
            "actual_counts_test": split_reports["test"]["actual_counts"],
            "predicted_counts_train": split_reports["train"]["predicted_counts"],
            "predicted_counts_validation": split_reports["validation"]["predicted_counts"],
            "predicted_counts_test": split_reports["test"]["predicted_counts"],
            "average_probabilities_train": split_reports["train"]["average_probabilities"],
            "average_probabilities_validation": split_reports["validation"]["average_probabilities"],
            "average_probabilities_test": split_reports["test"]["average_probabilities"],
            "confidence_distribution": {
                "train": split_reports["train"]["confidence_distribution"],
                "validation": split_reports["validation"]["confidence_distribution"],
                "test": split_reports["test"]["confidence_distribution"],
            },
            "confusion_matrix_train": split_reports["train"]["confusion_matrix"],
            "confusion_matrix_validation": split_reports["validation"]["confusion_matrix"],
            "confusion_matrix_test": split_reports["test"]["confusion_matrix"],
            "accuracy_train": split_reports["train"]["accuracy"],
            "accuracy_validation": split_reports["validation"]["accuracy"],
            "accuracy_test": split_reports["test"]["accuracy"],
            "brier_score_train": split_reports["train"]["brier_score"],
            "brier_score_validation": split_reports["validation"]["brier_score"],
            "brier_score_test": split_reports["test"]["brier_score"],
            "collapse_detected": collapse_detected,
            "collapse_reason": collapse_reason,
            "is_active": bool(model_row.is_active),
            "start_at": start_at.isoformat() if start_at is not None else None,
            "end_at": end_at.isoformat() if end_at is not None else None,
            "date_range_limited": start_at is not None and end_at is not None,
        }
        output_path = self._reports_dir / f"model_diagnostics_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def overfit_check(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        rows: int,
        epochs: int,
    ) -> dict[str, Any]:
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        split_rows = self._dataset_builder.split_rows(dataset_rows)
        train_rows = split_rows["train"][:rows]
        if len(train_rows) < rows and len(dataset_rows) >= rows:
            train_rows = sorted(dataset_rows, key=lambda item: item.candle_open_time)[:rows]
        if len(train_rows) < rows:
            raise ValueError(f"Requested {rows} rows for overfit-check, but only {len(train_rows)} train rows are available.")

        feature_columns = TrainingService.feature_columns()
        scaler = TrainingService.fit_scaler(train_rows, feature_columns)
        direction_class_weights = TrainingService.compute_direction_class_weights(train_rows)
        tensors = TrainingService.rows_to_tensors(train_rows, feature_columns, scaler)
        trainer = Trainer(
            epochs=epochs,
            learning_rate=1e-3,
            weight_decay=1e-4,
            loss_fn=MultiTaskLoss(direction_class_weights=direction_class_weights),
        )
        model = self._model_factory.create(model_name="candle_mlp", input_dim=len(feature_columns))
        training_result = trainer.train(model=model, train_dataset=tensors, validation_dataset=TrainingService.empty_tensors(len(feature_columns)))
        train_metrics = self._build_evaluator().evaluate(model, tensors)
        report = {
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "feature_version": feature_version,
            "label_version": label_version,
            "rows": rows,
            "epochs": epochs,
            "direction_class_weights": direction_class_weights,
            "random_baseline_accuracy": 1.0 / 3.0,
            "overfit_train_accuracy": train_metrics["accuracy"],
            "train_metrics": train_metrics,
            "training": training_result,
            "is_better_than_random_baseline": train_metrics["accuracy"] > (1.0 / 3.0),
        }
        output_path = self._reports_dir / f"overfit_check_{symbol.lower()}_{interval}_h{horizon_candles}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def confidence_report(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
    ) -> dict[str, Any]:
        predictions = self._build_prediction_rows(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=train_end,
            validation_end=validation_end,
        )
        return self._confidence_gate_evaluator.evaluate(model_version=model_version, predictions=predictions)

    def profit_report(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        take_profit_atr: float,
        stop_loss_atr: float,
        confidence_thresholds: list[float],
        train_end=None,
        validation_end=None,
    ) -> dict[str, Any]:
        predictions = self._build_prediction_rows(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=train_end,
            validation_end=validation_end,
        )
        return self._profit_aware_evaluator.evaluate(
            model_version=model_version,
            predictions=predictions,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            confidence_thresholds=confidence_thresholds,
        )

    def calibration_report(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
        start_at=None,
        end_at=None,
    ) -> dict[str, Any]:
        diagnostics = self.model_report(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=train_end,
            validation_end=validation_end,
            start_at=start_at,
            end_at=end_at,
        )
        predictions = self._build_prediction_rows(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=train_end,
            validation_end=validation_end,
            start_at=start_at,
            end_at=end_at,
        )
        return self._calibration_evaluator.evaluate(
            model_version=model_version,
            predictions=predictions,
            brier_score=diagnostics["brier_score_test"],
        )

    def probability_report(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
        start_at=None,
        end_at=None,
        label_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw_predictions = self._build_prediction_rows(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=train_end,
            validation_end=validation_end,
            start_at=start_at,
            end_at=end_at,
        )
        raw_report = self._prediction_probability_diagnostics.build_report(
            model_version=model_version,
            predictions=raw_predictions,
        )
        raw_report["collapse_v2"] = self._prediction_collapse_detector.detect(raw_report)
        calibrated_diagnostics = self._calibrated_prediction_decisions.build_report(
            predictions=raw_predictions,
            label_config=label_config,
            symbol=symbol,
            config_id=str(dict(label_config or {}).get("config_id") or label_version),
        )
        config_id = str(dict(label_config or {}).get("config_id") or label_version)
        calibrated_predictions = list(calibrated_diagnostics.get("calibrated_rows", []))
        selected_prediction_rows = list(calibrated_diagnostics.get("selected_rows", calibrated_predictions))
        selected_prediction_labels = [
            str(row.get("predicted_label", "FLAT")).upper()
            for row in selected_prediction_rows
            if isinstance(row, dict)
        ]
        prediction_decision_source = str(
            calibrated_diagnostics.get("selected_decision_source") or "calibrated_decision_layer"
        )
        decision_policy_grid_diagnostics: dict[str, Any] = {}
        if bool(dict(label_config or {}).get("decision_policy_grid_enabled", False)):
            actual_labels = [str(row.get("actual_label", "FLAT")).upper() for row in raw_predictions]
            decision_policy_grid_diagnostics = self._decision_policy_grid.evaluate(
                probability_rows=raw_predictions,
                actual_labels=actual_labels,
                baseline_accuracy=calibrated_diagnostics.get("baseline_accuracy"),
            )
            selected_prediction_labels = [
                str(label).upper()
                for label in decision_policy_grid_diagnostics.get("selected_predictions", [])
            ]
            selected_prediction_rows = self._rows_with_selected_predictions(
                source_rows=raw_predictions,
                selected_predictions=selected_prediction_labels,
                selected_decision_source=str(
                    decision_policy_grid_diagnostics.get("selected_decision_source")
                    or "decision_policy_grid:raw_argmax"
                ),
            )
            prediction_decision_source = str(
                decision_policy_grid_diagnostics.get("selected_decision_source")
                or prediction_decision_source
            )
        report = self._prediction_probability_diagnostics.build_report(
            model_version=model_version,
            predictions=selected_prediction_rows,
        )
        report["collapse_v2"] = self._prediction_collapse_detector.detect(report)
        calibrated_report = self._prediction_probability_diagnostics.build_report(
            model_version=model_version,
            predictions=calibrated_predictions,
        )
        calibrated_report["collapse_v2"] = self._prediction_collapse_detector.detect(calibrated_report)
        report["raw_probability_diagnostics"] = raw_report
        report["raw_collapse_v2"] = dict(raw_report.get("collapse_v2", {}))
        report["calibrated_probability_diagnostics"] = calibrated_report
        report["calibrated_collapse_v2"] = dict(calibrated_report.get("collapse_v2", {}))
        report["calibrated_decision_diagnostics"] = calibrated_diagnostics
        report["bounded_calibrated_decision_selection"] = dict(
            calibrated_diagnostics.get("bounded_calibrated_decision_selection", {})
        )
        report["prediction_root_cause_audit"] = self.build_prediction_root_cause_audit(
            prediction_rows=raw_predictions,
            symbol=symbol,
            config_id=config_id,
            decision_source=prediction_decision_source,
            selected_predictions=selected_prediction_labels,
        )
        report["book_driven_forensic_audit"] = self.build_book_driven_forensic_audit(
            prediction_rows=raw_predictions,
            candidate_payload={
                "symbol": symbol,
                "config_id": config_id,
                "model_accuracy": calibrated_diagnostics.get("selected_accuracy"),
                "baseline_accuracy": calibrated_diagnostics.get("baseline_accuracy"),
                "baseline_edge": calibrated_diagnostics.get("selected_baseline_edge"),
                "collapse_severity": dict(report.get("collapse_v2", {})).get("collapse_severity"),
                "prediction_decision_source": prediction_decision_source,
                "decision_policy_selected_policy_id": dict(decision_policy_grid_diagnostics).get("selected_policy_id"),
                "prediction_root_cause_audit": report["prediction_root_cause_audit"],
            },
        )
        report["schwager_slice_robustness"] = build_schwager_slice_robustness(
            selected_prediction_rows,
            label_mode=dict(label_config or {}).get("label_mode"),
        )
        if decision_policy_grid_diagnostics:
            report["decision_policy_grid_diagnostics"] = decision_policy_grid_diagnostics
        report["prediction_decision_source"] = prediction_decision_source
        report["start_at"] = start_at.isoformat() if start_at is not None else None
        report["end_at"] = end_at.isoformat() if end_at is not None else None
        report["date_range_limited"] = start_at is not None and end_at is not None
        output_path = self._reports_dir / f"probability_diagnostics_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def build_prediction_root_cause_audit(
        self,
        prediction_rows: list[dict[str, object]] | list[object],
        *,
        symbol: str | None = None,
        config_id: str | None = None,
        decision_source: str | None = None,
        selected_predictions: list[str] | None = None,
    ) -> dict[str, object]:
        """Build diagnostic-only root-cause audit for selected candidate predictions."""

        def _get(row: object, *names: str) -> object | None:
            if isinstance(row, dict):
                for name in names:
                    if name in row:
                        return row[name]
            for name in names:
                if hasattr(row, name):
                    return getattr(row, name)
            return None

        actual_labels: list[object] = []
        predicted_labels: list[object] = []
        probability_rows: list[dict[str, float]] = []
        split_names: list[object] = []
        regime_labels: list[object] = []
        timestamps: list[object] = []

        for index, row in enumerate(prediction_rows or []):
            actual = _get(row, "actual", "actual_label", "label", "target", "y_true")
            predicted = None
            if selected_predictions is not None and index < len(selected_predictions):
                predicted = selected_predictions[index]
            if predicted is None:
                predicted = _get(row, "prediction", "predicted", "predicted_label", "y_pred")

            actual_labels.append(actual)
            predicted_labels.append(predicted)
            probability_rows.append(
                {
                    "DOWN": float(_get(row, "prob_down", "prob_DOWN", "down_probability", "DOWN") or 0.0),
                    "FLAT": float(_get(row, "prob_flat", "prob_FLAT", "flat_probability", "FLAT") or 0.0),
                    "UP": float(_get(row, "prob_up", "prob_UP", "up_probability", "UP") or 0.0),
                }
            )
            split_names.append(_get(row, "split", "split_name", "dataset_split") or "unknown")
            regime_labels.append(_get(row, "regime", "market_regime", "regime_label") or "unknown")
            timestamps.append(_get(row, "open_time", "timestamp", "time"))

        auditor = PredictionRootCauseAuditor()
        return auditor.build(
            actual_labels=actual_labels,
            predicted_labels=predicted_labels,
            probability_rows=probability_rows,
            split_names=split_names,
            regime_labels=regime_labels,
            timestamps=timestamps,
            symbol=symbol,
            config_id=config_id,
            decision_source=decision_source,
        )

    def build_book_driven_forensic_audit(
        self,
        *,
        prediction_rows: list[dict[str, object]] | list[object],
        candidate_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return BookDrivenForensicAudit().evaluate(
            rows=prediction_rows,
            candidate_payload=candidate_payload,
        )

    @staticmethod
    def _rows_with_selected_predictions(
        *,
        source_rows: Sequence[dict[str, Any]],
        selected_predictions: Sequence[str],
        selected_decision_source: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row, selected_label in zip(source_rows, selected_predictions):
            selected_row = dict(row)
            selected_row["predicted_label"] = str(selected_label).upper()
            selected_row["selected_decision_source"] = selected_decision_source
            rows.append(selected_row)
        return rows

    def feature_diagnostics_v2(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
    ) -> dict[str, Any]:
        if self._label_repository is None:
            raise ValueError("Label repository is required for feature diagnostics v2.")
        feature_rows = self._feature_repository.get_all(symbol=symbol, interval=interval, feature_version=feature_version)
        label_rows = self._label_repository.get_all(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version=label_version,
        )
        report = self._feature_diagnostics_v2.build_report(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            feature_rows=feature_rows,
            labels_by_open_time={row.candle_open_time: row for row in label_rows},
        )
        output_path = self._reports_dir / f"feature_diagnostics_v2_{symbol}_{interval}_{feature_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def signal_gate_report(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
    ) -> dict[str, Any]:
        predictions = self._build_prediction_rows(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=train_end,
            validation_end=validation_end,
        )
        return self._signal_gate_evaluator.evaluate(model_version=model_version, predictions=predictions)

    def profit_report_v2(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
        train_end=None,
        validation_end=None,
        start_at=None,
        end_at=None,
    ) -> dict[str, Any]:
        predictions = self._build_prediction_rows(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=train_end,
            validation_end=validation_end,
            start_at=start_at,
            end_at=end_at,
        )
        return self._profit_aware_evaluator_v2.evaluate(
            model_version=model_version,
            predictions=predictions,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )

    def walk_forward_plan(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
    ) -> dict[str, Any]:
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        config = WalkForwardConfig(
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
        )
        plan = self._walk_forward_evaluator.build_plan(dataset_rows=dataset_rows, config=config)
        return self._walk_forward_evaluator.write_plan_report(symbol=symbol, interval=interval, label_version=label_version, plan=plan)

    def walk_forward_eval(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
        start_at=None,
        end_at=None,
    ) -> dict[str, Any]:
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            start_at=start_at,
            end_at=end_at,
        )
        config = WalkForwardConfig(
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
        )
        return self._walk_forward_evaluator.evaluate(
            model_version=model_version,
            label_version=label_version,
            dataset_rows=dataset_rows,
            prediction_builder=lambda rows: self._build_prediction_rows_for_subset(
                model_version=model_version,
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                feature_version=feature_version,
                label_version=label_version,
                target_rows=rows,
            ),
            config=config,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )

    def fold_label_diagnostics(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
    ) -> dict[str, Any]:
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        config = self._walk_forward_config(mode, train_days, validation_days, test_days, step_days, min_train_rows)
        plan = self._walk_forward_splitter.build_plan(dataset_rows, config)
        fold_payloads = []
        for fold in plan:
            split_rows = self._walk_forward_splitter.apply_fold(dataset_rows, fold)
            fold_payloads.append(
                {
                    **fold,
                    "train_rows_data": split_rows["train"],
                    "validation_rows_data": split_rows["validation"],
                    "test_rows_data": split_rows["test"],
                }
            )
        report = self._fold_label_diagnostics.build_report(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            folds=fold_payloads,
        )
        output_path = self._reports_dir / f"fold_label_diagnostics_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def directional_opportunity_diagnostics(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for directional opportunity diagnostics.")
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        config = self._walk_forward_config(mode, train_days, validation_days, test_days, step_days, min_train_rows)
        plan = self._walk_forward_splitter.build_plan(dataset_rows, config)
        fold_reports: list[dict[str, Any]] = []
        for fold in plan:
            split_rows = self._walk_forward_splitter.apply_fold(dataset_rows, fold)
            validation_long = self._evaluate_directional_side(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                target_rows=split_rows["validation"],
                predicted_label="UP",
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
            )
            validation_short = self._evaluate_directional_side(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                target_rows=split_rows["validation"],
                predicted_label="DOWN",
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
            )
            test_long = self._evaluate_directional_side(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                target_rows=split_rows["test"],
                predicted_label="UP",
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
            )
            test_short = self._evaluate_directional_side(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                target_rows=split_rows["test"],
                predicted_label="DOWN",
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
            )
            fold_reports.append(
                self._directional_opportunity_diagnostics.build_fold_report(
                    fold=fold,
                    validation_long=validation_long["summary"],
                    validation_short=validation_short["summary"],
                    test_long=test_long["summary"],
                    test_short=test_short["summary"],
                )
            )

        report = self._directional_opportunity_diagnostics.build_report(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            folds=fold_reports,
        )
        output_path = self._reports_dir / f"directional_opportunity_diagnostics_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def directional_baselines(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
        require_both_directions: bool = True,
    ) -> dict[str, Any]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for directional baselines.")
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        config = self._walk_forward_config(mode, train_days, validation_days, test_days, step_days, min_train_rows)
        return self._directional_baseline_evaluator.evaluate(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            dataset_rows=dataset_rows,
            config=config,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
            prediction_row_builder=lambda rows, labels: self._build_rule_prediction_rows(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                target_rows=rows,
                predicted_labels=labels,
            ),
            require_both_directions=require_both_directions,
        )

    def model_vs_baseline(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
    ) -> dict[str, Any]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for model-vs-baseline comparison.")
        walk_forward_report = self._load_first(self._reports_dir.glob("*.json"), f"walk_forward_eval_{model_version}.json")
        if walk_forward_report is None:
            raise ValueError(f"walk-forward report not found for model_version: {model_version}")

        baseline_report = self.directional_baselines(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            mode="expanding",
            train_days=45,
            validation_days=10,
            test_days=10,
            step_days=10,
            min_train_rows=1000,
            take_profit_atr=1.5,
            stop_loss_atr=1.0,
            fee_r=0.02,
            slippage_r=0.01,
            same_candle_policy="conservative",
            require_both_directions=True,
        )
        best_baseline = baseline_report.get("best_baseline", {})
        best_baseline_name = best_baseline.get("name")
        best_baseline_summary = best_baseline.get("summary") or {}
        comparison = self._model_vs_baseline_comparator.compare(
            model_version=model_version,
            feature_version=feature_version,
            label_version=label_version,
            walk_forward_summary=self._walk_forward_summary_with_global_metrics(walk_forward_report),
            baseline_name=best_baseline_name,
            baseline_summary=best_baseline_summary,
        )
        output_path = self._reports_dir / f"model_vs_baseline_{model_version}.json"
        output_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
        comparison["report_path"] = str(output_path)
        return comparison

    def prediction_bias_root_cause(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
    ) -> dict[str, Any]:
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        split_rows = self._dataset_builder.split_rows(dataset_rows, train_end=train_end, validation_end=validation_end)
        split_payloads = {
            split_name: {
                "split_name": split_name,
                "rows": rows,
                "predictions": self._build_prediction_rows_for_subset(
                    model_version=model_version,
                    symbol=symbol,
                    interval=interval,
                    horizon_candles=horizon_candles,
                    feature_version=feature_version,
                    label_version=label_version,
                    target_rows=rows,
                ),
            }
            for split_name, rows in split_rows.items()
        }
        report = self._prediction_bias_root_cause.build_report(
            model_version=model_version,
            label_version=label_version,
            split_payloads=split_payloads,
        )
        report["train_end"] = train_end.isoformat() if train_end is not None else None
        report["validation_end"] = validation_end.isoformat() if validation_end is not None else None
        output_path = self._reports_dir / f"prediction_bias_root_cause_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def compare_models(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
        start_at=None,
        end_at=None,
        model_versions: Sequence[str] | None = None,
        skip_incompatible_models: bool = True,
    ) -> dict[str, Any]:
        """Сравнивает модели с baseline без автоактивации.

        ML38.8 изменил архитектуру CandleMLP. В registry могут оставаться
        старые artifacts старой архитектуры. Общий compare_models не должен
        падать только из-за legacy artifact, если его можно безопасно пропустить.

        Для runtime candidate pipeline нужно передавать:
        - model_versions=[current_model]
        - skip_incompatible_models=False

        В этом режиме текущая модель обязана загружаться чисто. Если текущий
        artifact не грузится, это реальная техническая ошибка candidate.
        """

        baseline_service = BaselineService(dataset_builder=self._dataset_builder, reports_dir=self._reports_dir)
        baseline_report = baseline_service.evaluate(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            train_end=train_end,
            validation_end=validation_end,
            start_at=start_at,
            end_at=end_at,
        )

        requested_model_versions = tuple(str(item) for item in (model_versions or ()) if item)
        requested_model_version_set = set(requested_model_versions)

        model_rows = [
            row
            for row in self._model_registry_repository.list_all()
            if row["symbol"] == symbol
            and row["interval"] == interval
            and row["horizon_candles"] == horizon_candles
            and row["feature_version"] == feature_version
            and row["label_version"] == label_version
        ]

        if requested_model_version_set:
            model_rows = [
                row
                for row in model_rows
                if str(row.get("model_version")) in requested_model_version_set
            ]

        model_results: list[dict[str, Any]] = []
        skipped_model_errors: list[dict[str, Any]] = []

        profit_reports = {
            report.get("model_version"): report
            for report in self._load_matching(list(self._reports_dir.glob("*.json")), "profit_eval_")
        }
        confidence_reports = {
            report.get("model_version"): report
            for report in self._load_matching(list(self._reports_dir.glob("*.json")), "confidence_eval_")
        }
        calibration_reports = {
            report.get("model_version"): report
            for report in self._load_matching(list(self._reports_dir.glob("*.json")), "calibration_eval_")
        }

        for row in model_rows:
            model_version = str(row["model_version"])
            try:
                diagnostics = self.model_report(
                    model_version=model_version,
                    symbol=symbol,
                    interval=interval,
                    horizon_candles=horizon_candles,
                    feature_version=feature_version,
                    label_version=label_version,
                    train_end=train_end,
                    validation_end=validation_end,
                    start_at=start_at,
                    end_at=end_at,
                )
            except Exception as exc:
                if not skip_incompatible_models:
                    raise
                skipped_model_errors.append(
                    {
                        "model_version": model_version,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "reason": "model_report_failed_or_incompatible_artifact",
                    }
                )
                continue

            profit_report = profit_reports.get(model_version)
            confidence_report = confidence_reports.get(model_version)
            calibration_report = calibration_reports.get(model_version)

            best_profit_threshold = None
            if profit_report is not None and profit_report.get("thresholds"):
                best_profit_threshold = max(
                    profit_report["thresholds"],
                    key=lambda item: (item.get("profit_factor", 0.0), item.get("total_r", 0.0)),
                )

            best_confidence_threshold = None
            if confidence_report is not None and confidence_report.get("thresholds"):
                best_confidence_threshold = max(
                    confidence_report["thresholds"],
                    key=lambda item: (item.get("accuracy_on_signals", 0.0), item.get("coverage", 0.0)),
                )

            model_results.append(
                {
                    "model_version": model_version,
                    "is_active": row["is_active"],
                    "accuracy": diagnostics["accuracy_test"],
                    "brier_score": diagnostics["brier_score_test"],
                    "collapse_detected": diagnostics["collapse_detected"],
                    "collapse_reason": diagnostics["collapse_reason"],
                    "predicted_counts_test": diagnostics["predicted_counts_test"],
                    "actual_counts_test": diagnostics["actual_counts_test"],
                    "best_confidence_eval": best_confidence_threshold,
                    "best_profit_eval": best_profit_threshold,
                    "calibration_eval": calibration_report,
                    "report_path": diagnostics["report_path"],
                }
            )

        baselines = baseline_report.get("baselines") or {}
        if not baselines:
            raise ValueError("Baseline comparison produced no baselines.")

        best_baseline_name, best_baseline_result = max(
            baselines.items(),
            key=lambda item: self._score_tuple(item[1]["test"]["accuracy"], item[1]["test"]["brier_score"]),
        )

        best_model = (
            max(
                model_results,
                key=lambda item: self._score_tuple(item["accuracy"], item["brier_score"]),
            )
            if model_results
            else None
        )

        is_better = False
        if best_model is not None:
            is_better = self._score_tuple(best_model["accuracy"], best_model["brier_score"]) > self._score_tuple(
                best_baseline_result["test"]["accuracy"],
                best_baseline_result["test"]["brier_score"],
            )

        report = {
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "feature_version": feature_version,
            "label_version": label_version,
            "requested_model_versions": list(requested_model_versions),
            "compared_model_versions": [item["model_version"] for item in model_results],
            "skipped_model_count": len(skipped_model_errors),
            "skipped_model_errors": skipped_model_errors,
            "baseline_results": baselines,
            "model_results": model_results,
            "best_baseline": {
                "name": best_baseline_name,
                "test_metrics": best_baseline_result["test"],
            },
            "best_model": best_model,
            "is_best_model_better_than_best_baseline": is_better,
            "notes": (
                "Recommendation only. No model activation is performed automatically."
                if is_better
                else "Best model does not outperform the best baseline on current comparison."
            ),
        }

        output_path = self._reports_dir / f"model_comparison_{symbol.lower()}_{interval}_h{horizon_candles}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def experiment_summary(self, symbol: str, interval: str) -> dict[str, Any]:
        reports = list(self._reports_dir.glob("*.json"))
        grid_search = self._load_first(reports, f"label_grid_search_{symbol.lower()}_{interval}.json")
        comparisons = self._load_matching(reports, f"model_comparison_{symbol.lower()}_{interval}_h")
        profits = self._load_matching(reports, "profit_eval_")
        calibrations = self._load_matching(reports, "calibration_eval_")

        best_label_config = None
        if grid_search is not None:
            ok_candidates = [candidate for candidate in grid_search.get("candidates", []) if candidate["reject_reason"] == "ok"]
            if ok_candidates:
                best_label_config = max(ok_candidates, key=lambda item: item["candidate_score"])

        best_model_by_accuracy = self._best_model_from_comparisons(comparisons, key="accuracy")
        best_model_by_profit_factor, best_model_by_total_r = self._best_models_from_profit(profits)
        best_model_by_calibration = self._best_model_from_calibration(calibrations)

        recommended_model_version = None
        recommended_confidence_threshold = None
        recommended_label_version = None
        warnings: list[str] = []

        if best_model_by_accuracy is None:
            warnings.append("No model is better than baseline by accuracy.")
        else:
            best_profit = self._best_threshold_for_model(profits, best_model_by_accuracy["model_version"])
            if best_profit is None:
                warnings.append("No profit evaluation found for the best accuracy model.")
            elif best_profit["profit_factor"] <= 1.0:
                warnings.append("Best accuracy model has profit_factor <= 1.0.")
            elif best_profit["signal_count"] < 50:
                warnings.append("Best accuracy model has signal_count < 50.")
            else:
                recommended_model_version = best_model_by_accuracy["model_version"]
                recommended_confidence_threshold = best_profit["threshold"]
                recommended_label_version = best_model_by_accuracy.get("label_version")

        summary = {
            "best_label_config": best_label_config,
            "best_model_by_accuracy": best_model_by_accuracy,
            "best_model_by_profit_factor": best_model_by_profit_factor,
            "best_model_by_total_r": best_model_by_total_r,
            "best_model_by_calibration": best_model_by_calibration,
            "recommended_model_version": recommended_model_version,
            "recommended_confidence_threshold": recommended_confidence_threshold,
            "recommended_label_version": recommended_label_version,
            "warnings": warnings,
        }
        output_path = self._reports_dir / "stage_ml8_experiment_summary.json"
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        summary["report_path"] = str(output_path)
        return summary

    def experiment_summary_v2(self, symbol: str, interval: str) -> dict[str, Any]:
        reports = list(self._reports_dir.glob("*.json"))
        probabilities = {
            report.get("model_version"): report
            for report in self._load_matching(reports, "probability_diagnostics_")
        }
        signal_gates = {
            report.get("model_version"): report
            for report in self._load_matching(reports, "signal_gate_eval_")
        }
        profit_reports = {
            report.get("model_version"): report
            for report in self._load_matching(reports, "profit_eval_v2_")
        }
        calibration_reports = {
            report.get("model_version"): report
            for report in self._load_matching(reports, "calibration_eval_")
        }
        comparisons = self._load_matching(reports, f"model_comparison_{symbol.lower()}_{interval}_h")
        comparison_by_model = self._comparison_by_model(comparisons)

        best_model_by_accuracy = self._best_model_from_comparisons(comparisons, key="accuracy")
        best_model_by_calibration = self._best_model_from_calibration(list(calibration_reports.values()))
        best_model_by_profit_factor, best_model_by_total_r = self._best_models_from_profit_v2(list(profit_reports.values()))
        best_signal_gate_by_accuracy = self._best_signal_gate_result(list(signal_gates.values()))

        candidate_rows: list[dict[str, Any]] = []
        reject_reasons: list[str] = []
        for model_version, profit_report in profit_reports.items():
            probability_report = probabilities.get(model_version, {})
            collapse_v2 = probability_report.get("collapse_v2", {})
            comparison = comparison_by_model.get(model_version, {})
            for row in profit_report.get("gate_results", []):
                entry = {
                    "model_version": model_version,
                    "label_version": comparison.get("label_version"),
                    "gate_type": row.get("gate_type"),
                    "gate_threshold": row.get("threshold"),
                    "signal_count": row.get("signal_count", 0),
                    "profit_factor": row.get("profit_factor"),
                    "total_r": row.get("total_r", 0.0),
                    "expectancy_r": row.get("expectancy_r"),
                    "collapse_detected": bool(collapse_v2.get("collapse_detected", False)),
                    "dominant_class_ratio": float(collapse_v2.get("dominant_class_ratio", 0.0)),
                    "better_than_baseline": bool(comparison.get("better_than_baseline", False)),
                    "predicted_direction_counts": probability_report.get("predicted_direction_counts"),
                }
                entry["candidate_reject_reasons"] = self._recommendation_reasons(entry)
                reject_reasons.extend(entry["candidate_reject_reasons"])
                if not entry["candidate_reject_reasons"]:
                    candidate_rows.append(entry)

        recommended_model_version = None
        recommended_gate_type = None
        recommended_gate_threshold = None
        recommended_label_version = None
        warnings: list[str] = []

        if not best_model_by_profit_factor:
            warnings.append("no_profit_eligible_model_found")

        if candidate_rows:
            best_candidate = max(
                candidate_rows,
                key=lambda item: (
                    float(item["profit_factor"]),
                    float(item["total_r"]),
                    float(item["expectancy_r"]),
                    int(item["signal_count"]),
                ),
            )
            recommended_model_version = best_candidate["model_version"]
            recommended_gate_type = best_candidate["gate_type"]
            recommended_gate_threshold = best_candidate["gate_threshold"]
            recommended_label_version = best_candidate["label_version"]

        summary = {
            "symbol": symbol,
            "interval": interval,
            "best_model_by_accuracy": best_model_by_accuracy,
            "best_signal_gate_by_accuracy": best_signal_gate_by_accuracy,
            "best_model_by_profit_factor": best_model_by_profit_factor,
            "best_model_by_total_r": best_model_by_total_r,
            "best_model_by_calibration": best_model_by_calibration,
            "recommended_model_version": recommended_model_version,
            "recommended_gate_type": recommended_gate_type,
            "recommended_gate_threshold": recommended_gate_threshold,
            "recommended_label_version": recommended_label_version,
            "reject_reasons": sorted(set(reject_reasons)),
            "warnings": warnings,
        }
        output_path = self._reports_dir / "stage_ml9_experiment_summary.json"
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        summary["report_path"] = str(output_path)
        return summary

    def robust_experiment_summary(self, symbol: str, interval: str, require_both_directions: bool = True) -> dict[str, Any]:
        reports = self._load_matching(list(self._reports_dir.glob("*.json")), "walk_forward_eval_")
        candidates: list[dict[str, Any]] = []
        reject_reasons: list[str] = []
        for report in reports:
            if not report.get("model_version"):
                continue
            summary = self._walk_forward_summary_with_global_metrics(report)
            reasons = self._robust_reject_reasons(summary, require_both_directions=require_both_directions)
            if reasons:
                reject_reasons.extend(reasons)
                continue
            candidates.append(
                {
                    "model_version": report["model_version"],
                    "label_version": report.get("label_version"),
                    "gate_type": self._dominant_gate_type(summary.get("stable_gate_types", {})),
                    "gate_threshold": self._dominant_gate_threshold(report.get("folds", [])),
                    "walk_forward_total_r": summary.get("global_total_r"),
                    "walk_forward_profit_factor": summary.get("global_profit_factor"),
                    "walk_forward_signal_count": summary.get("total_test_signal_count"),
                    "profitable_fold_ratio": summary.get("profitable_fold_ratio"),
                    "avg_test_expectancy_r": summary.get("global_expectancy_r"),
                    "global_total_r": summary.get("global_total_r"),
                    "global_profit_factor": summary.get("global_profit_factor"),
                    "global_expectancy_r": summary.get("global_expectancy_r"),
                    "global_win_rate": summary.get("global_win_rate"),
                    "global_max_drawdown_r": summary.get("global_max_drawdown_r"),
                }
            )
        recommended = None
        if candidates:
            recommended = max(
                candidates,
                key=lambda item: (
                    float(item["global_total_r"]),
                    float(item["global_profit_factor"]),
                    float(item["global_expectancy_r"]),
                    int(item["walk_forward_signal_count"]),
                ),
            )
        result = {
            "symbol": symbol,
            "interval": interval,
            "require_both_directions": require_both_directions,
            "robust_recommended_model_version": recommended["model_version"] if recommended else None,
            "recommended_gate_type": recommended["gate_type"] if recommended else None,
            "recommended_gate_threshold": recommended["gate_threshold"] if recommended else None,
            "label_version": recommended["label_version"] if recommended else None,
            "walk_forward_total_r": recommended["walk_forward_total_r"] if recommended else None,
            "walk_forward_profit_factor": recommended["walk_forward_profit_factor"] if recommended else None,
            "walk_forward_signal_count": recommended["walk_forward_signal_count"] if recommended else None,
            "profitable_fold_ratio": recommended["profitable_fold_ratio"] if recommended else None,
            "global_total_r": recommended["global_total_r"] if recommended else None,
            "global_profit_factor": recommended["global_profit_factor"] if recommended else None,
            "global_expectancy_r": recommended["global_expectancy_r"] if recommended else None,
            "global_win_rate": recommended["global_win_rate"] if recommended else None,
            "global_max_drawdown_r": recommended["global_max_drawdown_r"] if recommended else None,
            "reject_reasons": sorted(set(reject_reasons)),
        }
        output_path = self._reports_dir / "robust_experiment_summary.json"
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["report_path"] = str(output_path)
        return result

    def stage_ml11_summary(self, symbol: str, interval: str) -> dict[str, Any]:
        reports = list(self._reports_dir.glob("*.json"))
        fold_labels = self._load_first_matching(reports, "fold_label_diagnostics_")
        opportunities = self._load_first_matching(reports, "directional_opportunity_diagnostics_")
        directional_baselines = self._load_first_matching(reports, "directional_baselines_")
        bias_reports = self._load_matching(reports, "prediction_bias_root_cause_")
        robust_summary = self._load_first(reports, "robust_experiment_summary.json") or {}
        walk_forward_reports = self._load_matching(reports, "walk_forward_eval_")

        best_directional_baseline = None
        best_directional_baseline_total_r = None
        always_long_baseline_total_r = None
        always_short_baseline_total_r = None
        if directional_baselines:
            best_directional_baseline = directional_baselines.get("best_baseline", {}).get("name")
            best_summary = directional_baselines.get("best_baseline", {}).get("summary") or {}
            best_directional_baseline_total_r = best_summary.get("global_total_r")
            always_long_baseline_total_r = directional_baselines.get("baselines", {}).get("always_long", {}).get("summary", {}).get("global_total_r")
            always_short_baseline_total_r = directional_baselines.get("baselines", {}).get("always_short", {}).get("summary", {}).get("global_total_r")

        ml_best_global_total_r = None
        ml_best_global_profit_factor = None
        if walk_forward_reports:
            best_walk = max(
                walk_forward_reports,
                key=lambda item: float(self._walk_forward_summary_with_global_metrics(item).get("global_total_r", 0.0)),
            )
            best_walk_summary = self._walk_forward_summary_with_global_metrics(best_walk)
            ml_best_global_total_r = best_walk_summary.get("global_total_r")
            ml_best_global_profit_factor = best_walk_summary.get("global_profit_factor")

        all_models_long_only = bool(walk_forward_reports) and all(
            int(self._walk_forward_summary_with_global_metrics(report).get("short_total_count", 0)) == 0
            and int(self._walk_forward_summary_with_global_metrics(report).get("long_total_count", 0)) > 0
            for report in walk_forward_reports
        )
        labels_are_balanced_by_fold = bool(fold_labels and fold_labels.get("labels_are_balanced_by_fold", False))
        short_opportunities_exist = bool(opportunities and opportunities.get("summary", {}).get("short_opportunities_exist", False))
        ml_beats_directional_baseline = (
            best_directional_baseline_total_r is not None
            and ml_best_global_total_r is not None
            and float(ml_best_global_total_r) > float(best_directional_baseline_total_r)
        )
        likely_root_cause = self._likely_root_cause(
            labels_are_balanced_by_fold=labels_are_balanced_by_fold,
            short_opportunities_exist=short_opportunities_exist,
            all_models_long_only=all_models_long_only,
            ml_beats_directional_baseline=bool(ml_beats_directional_baseline),
            bias_reports=bias_reports,
            always_long_baseline_total_r=always_long_baseline_total_r,
            always_short_baseline_total_r=always_short_baseline_total_r,
        )
        recommended_next_action = self._recommended_next_action(likely_root_cause)
        report = {
            "symbol": symbol,
            "interval": interval,
            "labels_are_balanced_by_fold": labels_are_balanced_by_fold,
            "short_opportunities_exist": short_opportunities_exist,
            "always_long_baseline_total_r": always_long_baseline_total_r,
            "always_short_baseline_total_r": always_short_baseline_total_r,
            "best_directional_baseline": best_directional_baseline,
            "best_directional_baseline_total_r": best_directional_baseline_total_r,
            "ml_best_global_total_r": ml_best_global_total_r,
            "ml_best_global_profit_factor": ml_best_global_profit_factor,
            "ml_beats_directional_baseline": ml_beats_directional_baseline,
            "all_models_long_only": all_models_long_only,
            "likely_root_cause": likely_root_cause,
            "recommended_next_action": recommended_next_action,
            "robust_recommended_model_version": robust_summary.get("robust_recommended_model_version"),
            "robust_reject_reasons": robust_summary.get("reject_reasons", []),
        }
        output_path = self._reports_dir / "stage_ml11_direction_bias_root_cause_summary.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def stage_ml12_summary(self, symbol: str, interval: str) -> dict[str, Any]:
        reports = list(self._reports_dir.glob("*.json"))
        feature_report_name = f"feature_diagnostics_v2_{symbol}_{interval}_fv2_regime.json"
        feature_report = self._load_first(reports, feature_report_name) or {}
        dataset_reports = [
            self._load_json(path)
            for path in self._reports_dir.glob(f"dataset_summary_{symbol.lower()}_{interval}_h*_fv2_regime_*.json")
        ]
        fv2_models = [
            row
            for row in self._model_registry_repository.list_all()
            if row["symbol"] == symbol and row["interval"] == interval and row["feature_version"] == "fv2_regime"
        ]
        fv2_models = sorted(fv2_models, key=lambda item: item["created_at"] or "", reverse=True)[:2]
        model_versions = [row["model_version"] for row in fv2_models]
        comparisons = []
        for model_version in model_versions:
            payload = self._load_first(reports, f"model_vs_baseline_{model_version}.json")
            if payload is not None:
                comparisons.append(payload)

        walk_forward_reports = {
            report["model_version"]: self._walk_forward_summary_with_global_metrics(report)
            for report in self._load_matching(reports, "walk_forward_eval_")
            if report.get("model_version") in model_versions
        }
        dominant_class_ratio_improved = any(
            float(summary.get("dominant_class_ratio_max", 1.0)) < 0.90
            for summary in walk_forward_reports.values()
        )
        short_signals_restored = any(
            int(summary.get("short_total_count", 0)) > 0
            for summary in walk_forward_reports.values()
        )
        best_model_version = None
        if comparisons:
            best_model_version = max(comparisons, key=lambda item: float(item.get("model_global_total_r", 0.0)))["model_version"]

        best_comparison = None
        eligible = []
        for comparison in comparisons:
            summary = walk_forward_reports.get(comparison["model_version"], {})
            robust_reasons = self._robust_reject_reasons(summary, require_both_directions=True)
            enriched = dict(comparison)
            enriched["robust_reject_reasons"] = robust_reasons
            if comparison.get("recommendation_allowed") and not robust_reasons:
                eligible.append(enriched)
            if best_comparison is None or float(enriched.get("model_global_total_r", 0.0)) > float(best_comparison.get("model_global_total_r", 0.0)):
                best_comparison = enriched

        if eligible:
            eligible = sorted(
                eligible,
                key=lambda item: (
                    float(item.get("model_global_total_r", 0.0)),
                    float(item.get("model_global_profit_factor", 0.0) or 0.0),
                    float(item.get("model_global_expectancy_r", 0.0) or 0.0),
                ),
                reverse=True,
            )
        recommended_model_version = eligible[0]["model_version"] if eligible else None
        best_baseline = best_comparison["baseline_name"] if best_comparison is not None else "ema_9_21_direction"
        model_beats_baseline = any(bool(item.get("model_beats_baseline_by_total_r")) for item in comparisons)
        recommended_next_action = self._stage_ml12_next_action(
            dataset_reports=dataset_reports,
            comparisons=comparisons,
            short_signals_restored=short_signals_restored,
            dominant_class_ratio_improved=dominant_class_ratio_improved,
            recommended_model_version=recommended_model_version,
        )
        recommended_reject_reasons = []
        if recommended_model_version is None and best_comparison is not None:
            recommended_reject_reasons = list(best_comparison.get("reject_reasons", [])) + list(
                best_comparison.get("robust_reject_reasons", [])
            )
            recommended_reject_reasons = sorted(set(recommended_reject_reasons))
        summary = {
            "stage": "ML12",
            "feature_version": "fv2_regime",
            "models_trained": model_versions,
            "best_model_version": best_model_version,
            "best_baseline": best_baseline,
            "model_beats_baseline": model_beats_baseline,
            "short_signals_restored": short_signals_restored,
            "dominant_class_ratio_improved": dominant_class_ratio_improved,
            "recommended_model_version": recommended_model_version,
            "recommended_reject_reasons": recommended_reject_reasons,
            "recommended_next_action": recommended_next_action,
            "feature_count_fv1": len(feature_names_for_version("fv1")),
            "feature_count_fv2_regime": len(feature_names_for_version("fv2_regime")),
            "dataset_rows": {
                report.get("label_version"): report.get("dataset_rows")
                for report in dataset_reports
            },
            "model_reports": comparisons if comparisons else [],
            "feature_diagnostics_report": str(self._reports_dir / feature_report_name) if feature_report else None,
        }
        output_path = self._reports_dir / "stage_ml12_summary.json"
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        summary["report_path"] = str(output_path)
        return summary

    def regime_segment_diagnostics(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for regime segment diagnostics.")
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )

        def evaluate_side(rows, predicted_label: str) -> dict[str, Any]:
            if not rows:
                return self._empty_profit_summary()
            result = self._evaluate_directional_side(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                target_rows=rows,
                predicted_label=predicted_label,
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
            )
            return result["summary"]

        def evaluate_ema_baseline(rows) -> dict[str, Any]:
            if not rows:
                return self._empty_profit_summary()
            predictions = self._build_rule_prediction_rows(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                target_rows=rows,
                predicted_labels=BaselineByRegimeEvaluator._predicted_labels_for_baseline("ema_9_21_direction", rows),
            )
            return self._profit_aware_evaluator_v2.evaluate_single_gate(
                predictions=predictions,
                gate_type="directional_edge",
                threshold=0.0,
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
            )["summary"]

        report = self._regime_segment_diagnostics.build_report(
            dataset_rows=dataset_rows,
            long_evaluator=lambda rows: evaluate_side(rows, "UP"),
            short_evaluator=lambda rows: evaluate_side(rows, "DOWN"),
            ema_baseline_evaluator=evaluate_ema_baseline,
        )
        report.update(
            {
                "symbol": symbol,
                "interval": interval,
                "feature_version": feature_version,
                "label_version": label_version,
                "take_profit_atr": take_profit_atr,
                "stop_loss_atr": stop_loss_atr,
                "fee_r": fee_r,
                "slippage_r": slippage_r,
                "same_candle_policy": same_candle_policy,
            }
        )
        output_path = self._reports_dir / f"regime_segment_diagnostics_{symbol}_{interval}_{feature_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def baseline_by_regime(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for baseline-by-regime.")
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        config = self._walk_forward_config(mode, train_days, validation_days, test_days, step_days, min_train_rows)
        return self._baseline_by_regime_evaluator.evaluate(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            dataset_rows=dataset_rows,
            config=config,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
            prediction_row_builder=lambda rows, labels: self._build_rule_prediction_rows(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                target_rows=rows,
                predicted_labels=labels,
            ),
        )

    def build_ema_meta_labels(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for EMA meta labels.")
        feature_rows = self._feature_repository.get_all(symbol=symbol, interval=interval, feature_version=feature_version)
        candles = self._candle_repository.get_all(symbol=symbol, interval=interval)
        records = self._ema_meta_label_builder.build(
            feature_rows=feature_rows,
            candles=candles,
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            horizon_candles=horizon_candles,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )
        report = {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "horizon_candles": horizon_candles,
            "take_profit_atr": take_profit_atr,
            "stop_loss_atr": stop_loss_atr,
            "fee_r": fee_r,
            "slippage_r": slippage_r,
            "same_candle_policy": same_candle_policy,
            **self._ema_meta_label_builder.summarize(records),
            "rows": [record.to_summary_dict() for record in records],
        }
        output_path = self._reports_dir / f"ema_meta_labels_{symbol}_{interval}_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def meta_label_diagnostics(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
    ) -> dict[str, Any]:
        feature_rows = self._feature_repository.get_all(symbol=symbol, interval=interval, feature_version=feature_version)
        meta_labels = self._load_meta_label_records(symbol=symbol, interval=interval, label_version=label_version)
        report = self._meta_label_diagnostics.build_report(
            feature_rows=feature_rows,
            meta_labels=meta_labels,
            feature_version=feature_version,
            label_version=label_version,
        )
        report.update({"symbol": symbol, "interval": interval})
        output_path = self._reports_dir / f"meta_label_diagnostics_{symbol}_{interval}_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def build_meta_dataset(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
    ) -> dict[str, Any]:
        dataset_rows, summary, split_rows = self._build_meta_dataset_rows(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
        )
        report = {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            **summary,
            "train_rows": len(split_rows["train"]),
            "validation_rows": len(split_rows["validation"]),
            "test_rows": len(split_rows["test"]),
        }
        output_path = self._reports_dir / f"meta_dataset_{symbol}_{interval}_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def meta_baselines(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
    ) -> dict[str, Any]:
        dataset_rows, _, _ = self._build_meta_dataset_rows(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
        )
        config = self._walk_forward_config(mode, train_days, validation_days, test_days, step_days, min_train_rows)
        return self._meta_baseline_evaluator.evaluate(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
            dataset_rows=dataset_rows,
            config=config,
        )

    def train_meta(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
    ) -> dict[str, Any]:
        dataset_rows, dataset_summary, split_rows = self._build_meta_dataset_rows(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
        )
        result = self._meta_training_service.train(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            dataset_rows=dataset_rows,
            dataset_summary=dataset_summary,
            split_rows=split_rows,
        )
        if not result.get("meta_training_skipped", False):
            train_rows = split_rows["train"]
            validation_rows = split_rows["validation"]
            test_rows = split_rows["test"]
            self._model_registry_repository.create(
                {
                    "model_name": "ema_meta_mlp_v1",
                    "model_version": result["model_version"],
                    "symbol": symbol,
                    "interval": interval,
                    "horizon_candles": horizon_candles,
                    "feature_version": feature_version,
                    "label_version": label_version,
                    "artifact_path": result["artifact_path"],
                    "train_start_at": train_rows[0].candle_open_time,
                    "train_end_at": train_rows[-1].candle_open_time,
                    "validation_start_at": validation_rows[0].candle_open_time if validation_rows else train_rows[-1].candle_open_time,
                    "validation_end_at": validation_rows[-1].candle_open_time if validation_rows else train_rows[-1].candle_open_time,
                    "test_start_at": test_rows[0].candle_open_time if test_rows else train_rows[-1].candle_open_time,
                    "test_end_at": test_rows[-1].candle_open_time if test_rows else train_rows[-1].candle_open_time,
                    "accuracy": result["test_metrics"].get("accuracy"),
                    "precision_up": result["test_metrics"].get("precision"),
                    "precision_down": None,
                    "brier_score": result["test_metrics"].get("brier_score"),
                    "tp_before_sl_accuracy": None,
                    "profit_factor": None,
                    "max_drawdown": None,
                    "is_active": False,
                }
            )
        output_path = self._reports_dir / f"meta_training_{symbol}_{interval}_{label_version}.json"
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["report_path"] = str(output_path)
        return result

    def evaluate_meta(self, model_version: str) -> dict[str, Any]:
        _, _, _, training_config, metrics = self._meta_training_service.load(model_version)
        report = {
            "model_version": model_version,
            "training_config": training_config,
            "train_metrics": metrics.get("train"),
            "validation_metrics": metrics.get("validation"),
            "test_metrics": metrics.get("test"),
            "dataset_summary": metrics.get("dataset_summary"),
        }
        output_path = self._reports_dir / f"meta_evaluation_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def walk_forward_meta_eval(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
        threshold_grid: list[float],
    ) -> dict[str, Any]:
        dataset_rows, _, _ = self._build_meta_dataset_rows(
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
            label_version=label_version,
        )
        config = self._walk_forward_config(mode, train_days, validation_days, test_days, step_days, min_train_rows)
        plan = self._walk_forward_splitter.build_plan(dataset_rows, config)
        folds: list[dict[str, Any]] = []
        for fold in plan:
            split_rows = self._walk_forward_splitter.apply_fold(dataset_rows, fold)
            validation_predictions = self._meta_training_service.build_prediction_rows(model_version, split_rows["validation"])
            validation_results = self._meta_gate_results(split_rows["validation"], validation_predictions, threshold_grid)
            selected_gate = self._select_meta_threshold(validation_results)
            test_result = None
            if selected_gate is not None:
                test_predictions = self._meta_training_service.build_prediction_rows(model_version, split_rows["test"])
                test_result = self._evaluate_meta_threshold(
                    split_rows["test"],
                    test_predictions,
                    float(selected_gate["threshold"]),
                )
            folds.append(
                {
                    **fold,
                    "selected_gate": selected_gate,
                    "validation_gate_results": validation_results,
                    "test_result": test_result,
                }
            )
        summary = self._summarize_meta_walk_forward(folds)
        report = {
            "model_version": model_version,
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "threshold_grid": threshold_grid,
            "folds": folds,
            "summary": summary,
        }
        output_path = self._reports_dir / f"walk_forward_meta_eval_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def stage_ml13_summary(self, symbol: str, interval: str) -> dict[str, Any]:
        reports = list(self._reports_dir.glob("*.json"))
        baseline_by_regime = self._load_first(reports, f"baseline_by_regime_{symbol}_{interval}_fv2_regime.json") or {}
        regime_segments = self._load_first(reports, f"regime_segment_diagnostics_{symbol}_{interval}_fv2_regime.json") or {}
        meta_labels = self._load_first(reports, f"ema_meta_labels_{symbol}_{interval}_meta_ema_9_21_tp15_sl10.json") or {}
        meta_label_diagnostics = self._load_first(reports, f"meta_label_diagnostics_{symbol}_{interval}_meta_ema_9_21_tp15_sl10.json") or {}
        meta_dataset = self._load_first(reports, f"meta_dataset_{symbol}_{interval}_meta_ema_9_21_tp15_sl10.json") or {}
        meta_baselines = self._load_first(reports, f"meta_baselines_{symbol}_{interval}_meta_ema_9_21_tp15_sl10.json") or {}
        meta_training = self._load_first(reports, f"meta_training_{symbol}_{interval}_meta_ema_9_21_tp15_sl10.json") or {}

        meta_model_version = meta_training.get("model_version")
        meta_training_skipped = bool(meta_training.get("meta_training_skipped", False)) or (
            bool(meta_dataset) and not bool(meta_dataset.get("meta_dataset_valid", False)) and meta_model_version is None
        )
        meta_evaluation = (
            self._load_first(reports, f"meta_evaluation_{meta_model_version}.json")
            if meta_model_version is not None
            else None
        )
        meta_walk_forward = (
            self._load_first(reports, f"walk_forward_meta_eval_{meta_model_version}.json")
            if meta_model_version is not None
            else None
        )
        take_all_summary = (
            meta_baselines.get("baselines", {})
            .get("take_all_ema_signals", {})
            .get("summary", {})
        )
        meta_model_beats_take_all_ema = False
        recommended_model_version = None
        recommended_meta_threshold = None
        reject_reasons: list[str] = []
        if meta_walk_forward is not None:
            walk_summary = meta_walk_forward.get("summary", {})
            dominant_threshold = self._dominant_meta_threshold(meta_walk_forward.get("folds", []))
            meta_model_beats_take_all_ema = (
                float(walk_summary.get("global_total_r", 0.0)) > float(take_all_summary.get("total_r", 0.0))
                and self._safe_float(walk_summary.get("global_profit_factor")) > self._safe_float(take_all_summary.get("global_profit_factor"))
            )
            if not meta_model_beats_take_all_ema:
                reject_reasons.append("meta_model_not_above_take_all_ema")
            if int(walk_summary.get("total_test_signal_count", 0)) < 50:
                reject_reasons.append("signal_count_lt_50")
            if int(walk_summary.get("long_total_count", 0)) == 0:
                reject_reasons.append("no_long_signals")
            if int(walk_summary.get("short_total_count", 0)) == 0:
                reject_reasons.append("no_short_signals")
            if float(walk_summary.get("profitable_fold_ratio", 0.0)) < 0.60:
                reject_reasons.append("profitable_fold_ratio_lt_0_60")
            if not reject_reasons:
                recommended_model_version = meta_model_version
                recommended_meta_threshold = dominant_threshold
        elif meta_dataset and not meta_dataset.get("meta_dataset_valid", False):
            reject_reasons.append("meta_dataset_invalid")
        elif meta_training_skipped:
            reject_reasons.append(meta_training.get("reason", "meta_training_skipped"))
        else:
            reject_reasons.append("meta_model_not_trained")

        recommended_next_action = self._stage_ml13_next_action(
            meta_dataset=meta_dataset,
            meta_training_skipped=meta_training_skipped,
            recommended_model_version=recommended_model_version,
            meta_model_version=meta_model_version,
        )
        report = {
            "best_baseline_overall": baseline_by_regime.get("best_baseline_overall", {}).get("baseline_name"),
            "best_baseline_total_r": baseline_by_regime.get("best_baseline_overall", {}).get("total_r"),
            "best_baseline_profit_factor": baseline_by_regime.get("best_baseline_overall", {}).get("global_profit_factor"),
            "regimes_where_ema_works": baseline_by_regime.get("regimes_where_ema_9_21_works", []),
            "regimes_where_ema_fails": baseline_by_regime.get("regimes_where_ema_9_21_fails", []),
            "meta_dataset_valid": bool(meta_dataset.get("meta_dataset_valid", False)),
            "meta_training_skipped": meta_training_skipped,
            "meta_model_version": meta_model_version,
            "meta_model_beats_take_all_ema": meta_model_beats_take_all_ema,
            "recommended_model_version": recommended_model_version,
            "recommended_meta_threshold": recommended_meta_threshold,
            "recommended_next_action": recommended_next_action,
            "reject_reasons": sorted(set(reject_reasons)),
            "regime_segment_report": regime_segments.get("report_path"),
            "baseline_by_regime_report": baseline_by_regime.get("report_path"),
            "ema_meta_labels_report": meta_labels.get("report_path"),
            "meta_label_diagnostics_report": meta_label_diagnostics.get("report_path"),
            "meta_dataset_report": meta_dataset.get("report_path"),
            "meta_baselines_report": meta_baselines.get("report_path"),
            "meta_evaluation_report": meta_evaluation.get("report_path") if meta_evaluation else None,
            "meta_walk_forward_report": meta_walk_forward.get("report_path") if meta_walk_forward else None,
        }
        output_path = self._reports_dir / "stage_ml13_regime_meta_label_summary.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    @staticmethod
    def _detect_collapse(predicted_counts: dict[str, int], total_rows: int) -> tuple[bool, str | None]:
        if total_rows == 0:
            return False, None
        dominant_label, dominant_count = max(predicted_counts.items(), key=lambda item: item[1])
        dominant_ratio = dominant_count / total_rows
        if dominant_ratio > 0.9:
            return True, f"{dominant_label} dominates test predictions: ratio={dominant_ratio:.4f}"
        return False, None

    @staticmethod
    def _score_tuple(accuracy: float, brier_score: float) -> tuple[float, float]:
        return accuracy, -brier_score

    def _build_prediction_rows(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
        start_at=None,
        end_at=None,
    ) -> list[dict[str, Any]]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for prediction-based diagnostics.")
        dataset_rows, _ = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            start_at=start_at,
            end_at=end_at,
        )
        split_rows = self._dataset_builder.split_rows(dataset_rows, train_end=train_end, validation_end=validation_end)
        return self._build_prediction_rows_for_subset(
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            target_rows=split_rows["test"],
        )

    def _build_prediction_rows_for_subset(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        target_rows,
    ) -> list[dict[str, Any]]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for prediction-based diagnostics.")

        model, scaler, feature_columns, training_config, metrics = self._model_loader.load(model_version)
        direction_temperature = direction_temperature_from_metadata(training_config, metrics)
        probability_source = "temperature_scaled" if direction_temperature != 1.0 else "raw_softmax"

        tensors = TrainingService.rows_to_tensors(target_rows, feature_columns, scaler)
        candle_rows = self._candle_repository.get_all(symbol=symbol, interval=interval)
        candles_by_open_time = {row.open_time: row for row in candle_rows}
        index_by_open_time = {row.open_time: index for index, row in enumerate(candle_rows)}
        if tensors["features"].shape[0] == 0:
            return []
        model.eval()
        with __import__("torch").no_grad():
            outputs = model(tensors["features"])
            probabilities = softmax_with_temperature(
                outputs["direction_logits"],
                temperature=direction_temperature,
            ).cpu().tolist()

        predictions: list[dict[str, Any]] = []
        index_to_label = {0: "UP", 1: "DOWN", 2: "FLAT"}
        for row, probability_row in zip(target_rows, probabilities):
            predicted_index = max(range(3), key=lambda idx: probability_row[idx])
            candle = candles_by_open_time[row.candle_open_time]
            candle_index = index_by_open_time[row.candle_open_time]
            future_window = candle_rows[candle_index + 1 : candle_index + 1 + horizon_candles]
            predictions.append(
                {
                    "candle_open_time": row.candle_open_time.isoformat(),
                    "actual_label": row.direction_label,
                    "predicted_label": index_to_label[predicted_index],
                    "prob_up": float(probability_row[0]),
                    "prob_down": float(probability_row[1]),
                    "prob_flat": float(probability_row[2]),
                    "confidence": float(max(probability_row)),
                    "direction_temperature": float(direction_temperature),
                    "probability_source": probability_source,
                    "future_move_atr": float(row.future_move_atr),
                    "max_favorable_move_atr": float(
                        getattr(row, "max_favorable_move_atr", row.future_move_atr)
                    ),
                    "max_adverse_move_atr": float(getattr(row, "max_adverse_move_atr", 0.0)),
                    "tp_before_sl": getattr(row, "tp_before_sl", None),
                    "setup_quality_score": float(getattr(row, "setup_quality_score", 0.0) or 0.0),
                    "setup_expected_move_atr": float(getattr(row, "setup_expected_move_atr", 0.0) or 0.0),
                    "setup_invalidation_distance_atr": float(
                        getattr(row, "setup_invalidation_distance_atr", 0.0) or 0.0
                    ),
                    "atr_14": float(row.features_json["atr_14"]),
                    "features_json": dict(row.features_json),
                    "current_close": float(candle.close),
                    "future_candles": [
                        {
                            "high": float(item.high),
                            "low": float(item.low),
                            "close": float(item.close),
                        }
                        for item in future_window
                    ],
                }
            )
        return self._apply_entry_path_filter_to_prediction_rows(
            predictions=predictions,
            feature_columns=feature_columns,
            training_config=training_config,
        )

    def _load_meta_label_records(self, symbol: str, interval: str, label_version: str) -> list[MetaLabelRecord]:
        path = self._reports_dir / f"ema_meta_labels_{symbol}_{interval}_{label_version}.json"
        if not path.exists():
            raise ValueError(f"EMA meta label report not found: {path.name}")
        payload = self._load_json(path)
        records: list[MetaLabelRecord] = []
        for row in payload.get("rows", []):
            records.append(
                MetaLabelRecord(
                    symbol=row["symbol"],
                    interval=row["interval"],
                    candle_open_time=datetime.fromisoformat(row["candle_open_time"]),
                    feature_version=row["feature_version"],
                    label_version=row["label_version"],
                    horizon_candles=int(row["horizon_candles"]),
                    ema_signal_direction=row["ema_signal_direction"],
                    ema_signal_strength_atr=row.get("ema_signal_strength_atr"),
                    meta_label=row["meta_label"],
                    meta_target_win=row.get("meta_target_win"),
                    meta_trade_r=row.get("meta_trade_r"),
                    meta_same_candle_ambiguous=bool(row.get("meta_same_candle_ambiguous", False)),
                )
            )
        return records

    def _build_meta_dataset_rows(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
    ) -> tuple[list[MetaDatasetRow], dict[str, Any], dict[str, list[MetaDatasetRow]]]:
        feature_rows = self._feature_repository.get_all(symbol=symbol, interval=interval, feature_version=feature_version)
        meta_labels = self._load_meta_label_records(symbol=symbol, interval=interval, label_version=label_version)
        dataset_rows, summary = self._meta_dataset_builder.build_rows(
            feature_rows=feature_rows,
            meta_labels=meta_labels,
            feature_version=feature_version,
        )
        split_rows = self._meta_dataset_builder.split_rows(dataset_rows)
        return dataset_rows, summary, split_rows

    @staticmethod
    def _empty_profit_summary() -> dict[str, Any]:
        return {
            "signal_count": 0,
            "resolved_signal_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "neither_count": 0,
            "gross_profit_r": 0.0,
            "gross_loss_r": 0.0,
            "profit_factor": None,
            "total_r": 0.0,
            "expectancy_r": None,
            "win_rate": None,
            "long_count": 0,
            "short_count": 0,
            "max_drawdown_r": 0.0,
            "global_profit_factor": None,
        }

    def _meta_gate_results(
        self,
        rows: list[MetaDatasetRow],
        predictions: list[dict[str, Any]],
        threshold_grid: list[float],
    ) -> list[dict[str, Any]]:
        return [self._evaluate_meta_threshold(rows, predictions, threshold) for threshold in threshold_grid]

    def _evaluate_meta_threshold(
        self,
        rows: list[MetaDatasetRow],
        predictions: list[dict[str, Any]],
        threshold: float,
    ) -> dict[str, Any]:
        probabilities_by_open_time = {
            item["candle_open_time"]: float(item["prob_win"])
            for item in predictions
        }
        filtered = [
            row
            for row in rows
            if probabilities_by_open_time.get(row.candle_open_time.isoformat(), 0.0) >= threshold
        ]
        summary = self._meta_baseline_evaluator.summarize_trade_rows(filtered)
        summary["threshold"] = threshold
        return summary

    @staticmethod
    def _select_meta_threshold(validation_results: list[dict[str, Any]]) -> dict[str, Any] | None:
        eligible = [row for row in validation_results if int(row.get("signal_count", 0)) > 0]
        if not eligible:
            return None
        best = max(
            eligible,
            key=lambda item: (
                float(item.get("total_r", 0.0)),
                DiagnosticsService._safe_float(item.get("global_profit_factor")),
                int(item.get("signal_count", 0)),
            ),
        )
        return {"gate_type": "prob_win", "threshold": float(best["threshold"])}

    def _summarize_meta_walk_forward(self, folds: list[dict[str, Any]]) -> dict[str, Any]:
        folds_with_selected_gate = [fold for fold in folds if fold.get("selected_gate") is not None]
        test_results = [fold["test_result"] for fold in folds_with_selected_gate if fold.get("test_result") is not None]
        signal_count = sum(int(item.get("signal_count", 0)) for item in test_results)
        total_r = sum(float(item.get("total_r", 0.0)) for item in test_results)
        long_count = sum(int(item.get("long_count", 0)) for item in test_results)
        short_count = sum(int(item.get("short_count", 0)) for item in test_results)
        gross_profit = sum(
            max(0.0, float(item.get("total_r", 0.0)))
            for item in test_results
        )
        gross_loss = abs(
            sum(min(0.0, float(item.get("total_r", 0.0))) for item in test_results)
        )
        if signal_count > 0:
            if gross_loss > 0:
                global_profit_factor = gross_profit / gross_loss
            elif gross_profit > 0:
                global_profit_factor = float("inf")
            else:
                global_profit_factor = 0.0
        else:
            global_profit_factor = None
        profitable_folds = sum(1 for item in test_results if float(item.get("total_r", 0.0)) > 0.0)
        return {
            "fold_count": len(folds),
            "folds_with_selected_gate": len(folds_with_selected_gate),
            "signal_count": signal_count,
            "total_test_signal_count": signal_count,
            "total_r": total_r,
            "global_total_r": total_r,
            "global_profit_factor": global_profit_factor,
            "expectancy_r": (total_r / signal_count) if signal_count else None,
            "global_expectancy_r": (total_r / signal_count) if signal_count else None,
            "profitable_fold_ratio": (profitable_folds / len(folds_with_selected_gate)) if folds_with_selected_gate else 0.0,
            "long_total_count": long_count,
            "short_total_count": short_count,
        }

    @staticmethod
    def _dominant_meta_threshold(folds: list[dict[str, Any]]) -> float | None:
        counts: dict[float, int] = {}
        for fold in folds:
            selected = fold.get("selected_gate")
            if selected is None:
                continue
            threshold = float(selected["threshold"])
            counts[threshold] = counts.get(threshold, 0) + 1
        if not counts:
            return None
        return max(counts.items(), key=lambda item: item[1])[0]

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_first(self, reports: list[Path], file_name: str) -> dict[str, Any] | None:
        for path in reports:
            if path.name == file_name:
                return self._load_json(path)
        return None

    def _load_matching(self, reports: list[Path], prefix: str) -> list[dict[str, Any]]:
        matched = []
        for path in reports:
            if path.name.startswith(prefix):
                payload = self._load_json(path)
                payload["_file_name"] = path.name
                matched.append(payload)
        return matched

    def _load_first_matching(self, reports: list[Path], prefix: str) -> dict[str, Any] | None:
        for path in reports:
            if path.name.startswith(prefix):
                return self._load_json(path)
        return None

    @staticmethod
    def _walk_forward_summary_with_global_metrics(report: dict[str, Any]) -> dict[str, Any]:
        summary = dict(report.get("summary", {}))
        if summary.get("global_total_r") is not None and summary.get("global_profit_factor") is not None:
            return summary

        folds = report.get("folds", [])
        test_results = [fold.get("test_result") for fold in folds if fold.get("test_result") is not None]
        global_profit = sum(float(item.get("gross_profit_r", 0.0)) for item in test_results)
        global_loss = sum(float(item.get("gross_loss_r", 0.0)) for item in test_results)
        global_total_r = sum(float(item.get("total_r", 0.0)) for item in test_results)
        global_wins = sum(int(item.get("win_count", 0)) for item in test_results)
        global_resolved = sum(
            int(item.get("resolved_signal_count", 0))
            or (
                int(item.get("win_count", 0))
                + int(item.get("loss_count", 0))
                + int(item.get("neither_count", 0))
            )
            for item in test_results
        )
        long_total_count = sum(int(item.get("long_count", 0)) for item in test_results)
        short_total_count = sum(int(item.get("short_count", 0)) for item in test_results)
        if global_resolved > 0:
            if global_loss > 0:
                global_profit_factor = global_profit / global_loss
            elif global_profit > 0:
                global_profit_factor = float("inf")
            else:
                global_profit_factor = 0.0
        else:
            global_profit_factor = None

        summary["global_gross_profit_r"] = global_profit
        summary["global_gross_loss_r"] = global_loss
        summary["global_profit_factor"] = global_profit_factor
        summary["global_total_r"] = global_total_r
        summary["global_expectancy_r"] = (global_total_r / global_resolved) if global_resolved else None
        summary["global_win_rate"] = (global_wins / global_resolved) if global_resolved else None
        summary["global_max_drawdown_r"] = max((float(item.get("max_drawdown_r", 0.0)) for item in test_results), default=0.0)
        summary["long_total_count"] = summary.get("long_total_count", long_total_count)
        summary["short_total_count"] = summary.get("short_total_count", short_total_count)
        return summary

    @staticmethod
    def _best_model_from_comparisons(comparisons: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
        models: list[dict[str, Any]] = []
        for comparison in comparisons:
            for model in comparison.get("model_results", []):
                model_copy = dict(model)
                model_copy["label_version"] = comparison.get("label_version")
                best_baseline_accuracy = comparison.get("best_baseline", {}).get("test_metrics", {}).get("accuracy")
                model_copy["better_than_baseline"] = (
                    best_baseline_accuracy is not None and model_copy.get("accuracy", 0.0) > best_baseline_accuracy
                )
                models.append(model_copy)
        if not models:
            return None
        filtered = [model for model in models if model.get("better_than_baseline")] or models
        return max(filtered, key=lambda item: item.get(key, 0.0))

    @staticmethod
    def _best_models_from_profit(profits: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        all_rows: list[dict[str, Any]] = []
        for report in profits:
            model_version = report.get("model_version")
            for row in report.get("thresholds", []):
                item = dict(row)
                item["model_version"] = model_version
                all_rows.append(item)
        if not all_rows:
            return None, None
        best_profit_factor = max(all_rows, key=lambda item: item.get("profit_factor", 0.0))
        best_total_r = max(all_rows, key=lambda item: item.get("total_r", 0.0))
        return best_profit_factor, best_total_r

    @staticmethod
    def _best_models_from_profit_v2(profits: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        eligible_rows: list[dict[str, Any]] = []
        for report in profits:
            for row in report.get("gate_results", []):
                if row.get("signal_count", 0) <= 0 or row.get("profit_factor") is None:
                    continue
                item = dict(row)
                item["model_version"] = report.get("model_version")
                eligible_rows.append(item)
        if not eligible_rows:
            return None, None
        best_profit_factor = max(
            eligible_rows,
            key=lambda item: (float(item.get("profit_factor", 0.0)), float(item.get("total_r", 0.0))),
        )
        best_total_r = max(
            eligible_rows,
            key=lambda item: (float(item.get("total_r", 0.0)), float(item.get("profit_factor", 0.0))),
        )
        return best_profit_factor, best_total_r

    @staticmethod
    def _best_signal_gate_result(signal_gate_reports: list[dict[str, Any]]) -> dict[str, Any] | None:
        rows: list[dict[str, Any]] = []
        for report in signal_gate_reports:
            model_version = report.get("model_version")
            for row in report.get("gate_results", []):
                item = dict(row)
                item["model_version"] = model_version
                rows.append(item)
        if not rows:
            return None
        return max(
            rows,
            key=lambda item: (
                float(item.get("accuracy_on_signals", 0.0)),
                float(item.get("coverage", 0.0)),
                -float(item.get("skipped_flat_count", 0.0)),
            ),
        )

    @staticmethod
    def _best_model_from_calibration(calibrations: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not calibrations:
            return None
        return min(
            calibrations,
            key=lambda item: (item.get("expected_calibration_error", float("inf")), item.get("brier_score", float("inf"))),
        )

    @staticmethod
    def _best_threshold_for_model(profits: list[dict[str, Any]], model_version: str) -> dict[str, Any] | None:
        rows: list[dict[str, Any]] = []
        for report in profits:
            if report.get("model_version") != model_version:
                continue
            rows.extend(report.get("thresholds", []))
        if not rows:
            return None
        return max(rows, key=lambda item: (item.get("profit_factor", 0.0), item.get("total_r", 0.0)))

    @staticmethod
    def _comparison_by_model(comparisons: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for comparison in comparisons:
            baseline_accuracy = comparison.get("best_baseline", {}).get("test_metrics", {}).get("accuracy")
            for model in comparison.get("model_results", []):
                rows[model["model_version"]] = {
                    "label_version": comparison.get("label_version"),
                    "better_than_baseline": (
                        baseline_accuracy is not None and model.get("accuracy", 0.0) > baseline_accuracy
                    ),
                }
        return rows

    @staticmethod
    def _recommendation_reasons(candidate: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        if int(candidate.get("signal_count", 0)) < 50:
            reasons.append("signal_count_lt_50")
        if candidate.get("profit_factor") is None:
            reasons.append("profit_factor_is_null")
        elif float(candidate["profit_factor"]) <= 1.0:
            reasons.append("profit_factor_not_above_1")
        if float(candidate.get("total_r", 0.0)) <= 0.0:
            reasons.append("total_r_not_positive")
        expectancy = candidate.get("expectancy_r")
        if expectancy is None or float(expectancy) <= 0.0:
            reasons.append("expectancy_r_not_positive")
        if not bool(candidate.get("better_than_baseline", False)):
            reasons.append("not_better_than_baseline")
        if bool(candidate.get("collapse_detected", False)):
            reasons.append("collapse_detected")
        if float(candidate.get("dominant_class_ratio", 0.0)) >= 0.90:
            reasons.append("dominant_class_ratio_gte_0_90")
        if candidate.get("gate_type") is None or candidate.get("gate_threshold") is None:
            reasons.append("gate_not_specified")
        return reasons

    @staticmethod
    def _robust_reject_reasons(summary: dict[str, Any], require_both_directions: bool = True) -> list[str]:
        reasons: list[str] = []
        if int(summary.get("fold_count", 0)) < 3:
            reasons.append("fold_count_lt_3")
        if int(summary.get("folds_with_selected_gate", 0)) < 2:
            reasons.append("folds_with_selected_gate_lt_2")
        if int(summary.get("total_test_signal_count", 0)) < 50:
            reasons.append("total_test_signal_count_lt_50")
        if float(summary.get("global_total_r", 0.0)) <= 0.0:
            reasons.append("global_total_r_not_positive")
        global_expectancy = summary.get("global_expectancy_r")
        if global_expectancy is None or float(global_expectancy) <= 0.0:
            reasons.append("global_expectancy_r_not_positive")
        if float(summary.get("profitable_fold_ratio", 0.0)) < 0.60:
            reasons.append("profitable_fold_ratio_lt_0_60")
        global_pf = summary.get("global_profit_factor")
        if global_pf is None or float(global_pf) <= 1.0:
            reasons.append("global_profit_factor_not_above_1")
        if float(summary.get("dominant_class_ratio_max", 0.0)) >= 0.90:
            reasons.append("dominant_class_ratio_gte_0_90")
        if require_both_directions:
            if int(summary.get("short_total_count", 0)) == 0:
                reasons.append("no_short_signals")
            if int(summary.get("long_total_count", 0)) == 0:
                reasons.append("no_long_signals")
        return reasons

    @staticmethod
    def _dominant_gate_type(stable_gate_types: dict[str, int]) -> str | None:
        if not stable_gate_types:
            return None
        return max(stable_gate_types.items(), key=lambda item: item[1])[0]

    @staticmethod
    def _dominant_gate_threshold(folds: list[dict[str, Any]]) -> float | None:
        counts: dict[float, int] = {}
        for fold in folds:
            selected = fold.get("selected_gate")
            if not selected:
                continue
            threshold = float(selected["threshold"])
            counts[threshold] = counts.get(threshold, 0) + 1
        if not counts:
            return None
        return max(counts.items(), key=lambda item: item[1])[0]

    @staticmethod
    def _walk_forward_config(
        mode: str,
        train_days: int,
        validation_days: int,
        test_days: int,
        step_days: int,
        min_train_rows: int,
    ) -> WalkForwardConfig:
        return WalkForwardConfig(
            mode=mode,
            train_days=train_days,
            validation_days=validation_days,
            test_days=test_days,
            step_days=step_days,
            min_train_rows=min_train_rows,
        )

    def _evaluate_directional_side(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        target_rows,
        predicted_label: str,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        predictions = self._build_rule_prediction_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            target_rows=target_rows,
            predicted_labels=[predicted_label] * len(target_rows),
        )
        return self._profit_aware_evaluator_v2.evaluate_single_gate(
            predictions=predictions,
            gate_type="directional_edge",
            threshold=0.0,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )

    def _apply_entry_path_filter_to_prediction_rows(
        self,
        *,
        predictions: list[dict[str, Any]],
        feature_columns: list[str] | tuple[str, ...],
        training_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Apply ML38.10.14 ex-ante entry-path filter to prediction rows.

        This is still research-only. It does not use realized MAE/MFE to decide.
        It uses feature context and setup fields already available on DatasetRow.
        """
        if not bool(training_config.get("entry_path_quality_filter_enabled", False)):
            return predictions

        entry_threshold = training_config.get("entry_path_quality_min_threshold")
        stop_threshold = training_config.get("stop_pressure_max_risk_score")
        if entry_threshold is None and stop_threshold is None:
            return predictions

        entry_threshold = 0.0 if entry_threshold is None else float(entry_threshold)
        stop_threshold = 1.0 if stop_threshold is None else float(stop_threshold)
        columns = list(feature_columns or [])

        feature_rows: list[list[float]] = []
        setup_quality_scores: list[float] = []
        expected_move_atr: list[float] = []
        invalidation_distance_atr: list[float] = []

        for row in predictions:
            features_json = row.get("features_json") if isinstance(row.get("features_json"), dict) else {}
            feature_rows.append([
                float(features_json.get(column, 0.0) or 0.0)
                for column in columns
            ])
            setup_quality_scores.append(float(row.get("setup_quality_score", 0.0) or 0.0))
            expected_move_atr.append(float(row.get("setup_expected_move_atr", 0.0) or 0.0))
            invalidation_distance_atr.append(
                float(row.get("setup_invalidation_distance_atr", 0.0) or 0.0)
            )

        predicted_labels = [
            str(row.get("entry_path_original_predicted_label", row.get("predicted_label", "")) or "").upper()
            for row in predictions
        ]
        score_payload = self._entry_path_quality_filter.score_rows(
            feature_names=columns,
            feature_rows=feature_rows,
            setup_quality_scores=setup_quality_scores,
            expected_move_atr=expected_move_atr,
            invalidation_distance_atr=invalidation_distance_atr,
            predicted_labels=predicted_labels,
            score_profile=training_config.get(
                "entry_path_quality_score_profile",
                "legacy_balanced_v1",
            ),
        )
        score_rows = list(score_payload.get("score_rows", []))

        filtered_rows: list[dict[str, Any]] = []
        for row, score in zip(predictions, score_rows):
            entry_score = float(score.get("entry_path_quality_score", 0.0) or 0.0)
            stop_score = float(score.get("stop_pressure_risk_score", 1.0) or 1.0)
            blocked = entry_score < entry_threshold or stop_score > stop_threshold
            enriched = dict(row)
            original_predicted_label = row.get(
                "entry_path_original_predicted_label",
                row.get("predicted_label"),
            )
            enriched.update(score)
            enriched["entry_path_filter_enabled"] = True
            enriched["entry_path_filter_threshold"] = entry_threshold
            enriched["entry_path_filter_stop_threshold"] = stop_threshold
            enriched["entry_path_filter_blocked"] = bool(blocked)
            enriched["entry_path_original_predicted_label"] = original_predicted_label
            enriched["entry_path_filtered_predicted_label"] = (
                "FLAT" if blocked else row.get("predicted_label")
            )
            if blocked:
                enriched["predicted_label"] = "FLAT"    
                enriched["entry_path_filter_block_reason"] = (
                    "low_entry_quality"
                    if entry_score < entry_threshold
                    else "high_stop_pressure"
                )
            else:
                enriched["entry_path_filter_block_reason"] = None
            filtered_rows.append(enriched)

        # If score_rows is unexpectedly shorter, keep remaining predictions unchanged.
        if len(filtered_rows) < len(predictions):
            filtered_rows.extend(predictions[len(filtered_rows):])

        return filtered_rows

    def _build_rule_prediction_rows(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        target_rows,
        predicted_labels: list[str],
    ) -> list[dict[str, Any]]:
        if self._candle_repository is None:
            raise ValueError("Candle repository is required for rule predictions.")
        candle_rows = self._candle_repository.get_all(symbol=symbol, interval=interval)
        candles_by_open_time = {row.open_time: row for row in candle_rows}
        index_by_open_time = {row.open_time: index for index, row in enumerate(candle_rows)}
        probability_map = {
            "UP": (1.0, 0.0, 0.0),
            "DOWN": (0.0, 1.0, 0.0),
            "FLAT": (0.0, 0.0, 1.0),
        }
        predictions: list[dict[str, Any]] = []
        for row, predicted_label in zip(target_rows, predicted_labels):
            candle = candles_by_open_time[row.candle_open_time]
            candle_index = index_by_open_time[row.candle_open_time]
            future_window = candle_rows[candle_index + 1 : candle_index + 1 + horizon_candles]
            prob_up, prob_down, prob_flat = probability_map[predicted_label]
            ordered = sorted((prob_up, prob_down, prob_flat), reverse=True)
            predictions.append(
                {
                    "candle_open_time": row.candle_open_time.isoformat(),
                    "actual_label": row.direction_label,
                    "predicted_label": predicted_label,
                    "prob_up": prob_up,
                    "prob_down": prob_down,
                    "prob_flat": prob_flat,
                    "confidence": ordered[0],
                    "margin": ordered[0] - ordered[1],
                    "directional_edge": abs(prob_up - prob_down),
                    "future_move_atr": float(row.future_move_atr),
                    "atr_14": float(row.features_json["atr_14"]),
                    "current_close": float(candle.close),
                    "future_candles": [
                        {
                            "high": float(item.high),
                            "low": float(item.low),
                            "close": float(item.close),
                        }
                        for item in future_window
                    ],
                }
            )
        return predictions

    @staticmethod
    def _likely_root_cause(
        labels_are_balanced_by_fold: bool,
        short_opportunities_exist: bool,
        all_models_long_only: bool,
        ml_beats_directional_baseline: bool,
        bias_reports: list[dict[str, Any]],
        always_long_baseline_total_r,
        always_short_baseline_total_r,
    ) -> str:
        if not labels_are_balanced_by_fold:
            return "label_imbalance"
        if not short_opportunities_exist and (always_long_baseline_total_r or 0.0) > (always_short_baseline_total_r or 0.0):
            return "market_regime_long_bias"
        if all_models_long_only and any("likely_training_bias" in report.get("warnings", []) for report in bias_reports):
            return "model_training_bias"
        if not ml_beats_directional_baseline and short_opportunities_exist:
            return "feature_insufficient_directional_signal"
        return "unknown"

    @staticmethod
    def _recommended_next_action(likely_root_cause: str) -> str:
        mapping = {
            "label_imbalance": "fix_labels",
            "market_regime_long_bias": "expand_history",
            "model_training_bias": "change_loss_or_sampler",
            "feature_insufficient_directional_signal": "add_regime_features",
            "profit_evaluator_bias": "add_direction_balancing",
            "unknown": "stop_ml_until_more_data",
        }
        return mapping.get(likely_root_cause, "stop_ml_until_more_data")

    @staticmethod
    def _stage_ml12_next_action(
        dataset_reports: list[dict[str, Any]],
        comparisons: list[dict[str, Any]],
        short_signals_restored: bool,
        dominant_class_ratio_improved: bool,
        recommended_model_version: str | None,
    ) -> str:
        if recommended_model_version is not None:
            return "prepare_manual_activation_review"
        if not dataset_reports or any(int(report.get("dataset_rows", 0)) == 0 for report in dataset_reports):
            return "stop_ml_until_more_data"
        if not short_signals_restored:
            return "fix_direction_balancing"
        if comparisons and not any(bool(item.get("model_beats_baseline_by_total_r")) for item in comparisons):
            return "add_more_regime_features"
        if not dominant_class_ratio_improved:
            return "fix_direction_balancing"
        return "expand_history"

    @staticmethod
    def _stage_ml13_next_action(
        meta_dataset: dict[str, Any],
        meta_training_skipped: bool,
        recommended_model_version: str | None,
        meta_model_version: str | None,
    ) -> str:
        if recommended_model_version is not None:
            return "prepare_manual_activation_review"
        if not meta_dataset:
            return "stop_ml_until_more_data"
        if not bool(meta_dataset.get("meta_dataset_valid", False)):
            if int(meta_dataset.get("dataset_rows", 0)) < 1000:
                return "expand_history"
            if int(meta_dataset.get("long_rows", 0)) == 0 or int(meta_dataset.get("short_rows", 0)) == 0:
                return "fix_direction_balancing"
            return "improve_meta_features"
        if meta_training_skipped:
            return "train_meta_model"
        if meta_model_version is None:
            return "train_meta_model"
        return "improve_meta_features"

    @staticmethod
    def _safe_float(value: Any) -> float:
        if value is None:
            return 0.0
        return float(value)

    def _build_evaluator(self):
        from app.training.evaluator import Evaluator

        return Evaluator()
