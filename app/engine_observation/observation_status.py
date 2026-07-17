from enum import StrEnum


class ObservationVerdict(StrEnum):
    PASSED = "OBSERVATION_PASSED"
    PASSED_WITH_WARNINGS = "OBSERVATION_PASSED_WITH_WARNINGS"
    FAILED = "OBSERVATION_FAILED"
    BLOCKED_INSUFFICIENT_WINDOW = "BLOCKED_INSUFFICIENT_WINDOW"
    BLOCKED_DATABASE = "BLOCKED_DATABASE"
    BLOCKED_SCHEMA = "BLOCKED_SCHEMA"
    BLOCKED_SERVICES_NOT_RUNNING = "BLOCKED_SERVICES_NOT_RUNNING"


def evaluate_verdict(*, coverage: dict, integrity: dict, safety: dict, latency: dict,
                     freshness_skip_count: int, error_count: int, sync_state: dict,
                     thresholds: object, fail_on_warning: bool = False) -> tuple[str, list[str], list[str]]:
    aggregate, checks = coverage["aggregate"], integrity["checks"]
    failures, warnings = [], []
    hard = {
        "safety violations": safety["violation_count"],
        "duplicates": aggregate["duplicate_windows"],
        "orphan result rows": checks["orphan_result_rows"],
        "future-boundary processing": latency["future_boundary_processing_count"],
        "invalid transitions": checks["invalid_transitions"],
        "negative duration": checks["negative_duration"],
    }
    failures.extend(f"{name}: {count}" for name, count in hard.items() if count)
    expected = aggregate["expected_windows"] or 1
    missing_ratio = aggregate["missing_windows"] / expected
    freshness_ratio = freshness_skip_count / expected
    if missing_ratio > thresholds.missing_fail_ratio: failures.append(f"missing window ratio {missing_ratio:.2%}")
    elif missing_ratio > thresholds.missing_warning_ratio: warnings.append(f"missing window ratio {missing_ratio:.2%}")
    if checks["stale_reservations"]: failures.append(f"stale reservations: {checks['stale_reservations']}")
    if freshness_ratio > thresholds.freshness_fail_ratio: failures.append(f"freshness skip ratio {freshness_ratio:.2%}")
    elif freshness_ratio > thresholds.freshness_warning_ratio: warnings.append(f"freshness skip ratio {freshness_ratio:.2%}")
    if aggregate["completion_ratio"] < thresholds.completion_warning_ratio:
        warnings.append(f"completion ratio {aggregate['completion_ratio']:.2%}")
    if error_count: warnings.append(f"module/error runs: {error_count}")
    p95 = latency["aggregate"]["end_to_end_latency_ms"]["p95"]
    if p95 is not None and p95 > thresholds.latency_fail_ms: failures.append(f"p95 end-to-end latency {p95:.0f} ms")
    elif p95 is not None and p95 > thresholds.latency_warning_ms: warnings.append(f"p95 end-to-end latency {p95:.0f} ms")
    if sync_state["non_ok_rows"]:
        message = f"current market_data_sync_state non-OK rows: {sync_state['non_ok_rows']}"
        (failures if sync_state["severe_rows"] else warnings).append(message)
    if failures or (fail_on_warning and warnings): return ObservationVerdict.FAILED.value, failures, warnings
    if warnings: return ObservationVerdict.PASSED_WITH_WARNINGS.value, failures, warnings
    return ObservationVerdict.PASSED.value, failures, warnings
