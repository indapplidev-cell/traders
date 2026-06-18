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

    ML38.8 изменил архитектуру CandleMLP. В registry могут оставаться старые
    artifacts старой архитектуры. Общий compare_models не должен падать только
    из-за legacy model artifact, если его можно пропустить.

    Для runtime candidate pipeline нужно передавать model_versions=[current_model]
    и skip_incompatible_models=False: текущая модель обязана загружаться чисто.
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
