from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from app.server_api.repositories.records import (
    AnalysisRecord,
    HealthRecord,
    IncidentRecord,
    MarketRecord,
    RunRecord,
    SetupRecord,
)
from app.server_api.schemas.models import (
    AnalysisSnapshot,
    AnalysisStatus,
    Direction,
    HealthSnapshot,
    HealthState,
    IncidentDetail,
    IncidentStatus,
    IncidentSummary,
    MarketDetail,
    MarketSummary,
    PipelineRunSummary,
    PipelineStatus,
    ServiceSnapshot,
    SetupDetail,
    SetupStatus,
    SetupSummary,
    Severity,
)


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("API timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def utc_from_ms(value: int) -> str:
    return utc_text(datetime.fromtimestamp(value / 1000, tz=timezone.utc))


def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not value.is_finite():
        raise ValueError("financial values must be finite")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text not in {"-0", ""} else "0"


def safe_enum(enum_type: type[StrEnum], value: str | None, fallback: str = "UNKNOWN") -> StrEnum:
    try:
        return enum_type(str(value))
    except ValueError:
        return enum_type(fallback)


class ContractMapper:
    def health(self, value: HealthRecord) -> HealthSnapshot:
        return HealthSnapshot(
            status=safe_enum(HealthState, value.status),
            observed_at=utc_text(value.observed_at),
            services=[
                ServiceSnapshot(
                    name=item.name,
                    status=safe_enum(HealthState, item.status),
                    observed_at=utc_text(item.observed_at),
                    message=item.message,
                )
                for item in value.services
            ],
        )

    def market_summary(self, value: MarketRecord) -> MarketSummary:
        boundary = utc_from_ms(value.closed_until_ms) if value.closed_until_ms is not None else None
        return MarketSummary(
            symbol=value.symbol.upper(),
            status=safe_enum(HealthState, value.status),
            latest_price=decimal_text(value.latest_price),
            closed_until=boundary,
            closed_until_ms=value.closed_until_ms,
            regime=value.regime,
            setup_status=safe_enum(SetupStatus, value.setup_status),
            risk_status=value.risk_status,
            updated_at=utc_text(value.updated_at),
        )

    def market_detail(self, value: MarketRecord) -> MarketDetail:
        if value.future_bars_used:
            raise ValueError("future bars cannot be exposed")
        return MarketDetail(
            summary=self.market_summary(value),
            timeframe=value.timeframe,
            open=decimal_text(value.open),
            high=decimal_text(value.high),
            low=decimal_text(value.low),
            close=decimal_text(value.close),
            volume=decimal_text(value.volume),
            has_gaps=value.has_gaps,
            enough_data=value.enough_data,
            future_bars_used=False,
        )

    def analysis(self, value: AnalysisRecord) -> AnalysisSnapshot:
        direction = safe_enum(Direction, value.direction)
        return AnalysisSnapshot(
            analysis_id=value.analysis_id,
            symbol=value.symbol.upper(),
            timeframe=value.timeframe,
            closed_until=utc_from_ms(value.closed_until_ms),
            closed_until_ms=value.closed_until_ms,
            status=safe_enum(AnalysisStatus, value.status),
            market_data_status=safe_enum(HealthState, value.market_data_status),
            regime=value.regime,
            direction=direction,
            confidence=value.confidence,
            impulse_phase=value.impulse_phase,
            entry_quality=value.entry_quality,
            reason_codes=list(value.reason_codes),
            updated_at=utc_text(value.updated_at),
        )

    def setup_summary(self, value: SetupRecord) -> SetupSummary:
        return SetupSummary(
            setup_id=value.setup_id,
            symbol=value.symbol.upper(),
            timeframe=value.timeframe,
            closed_until=utc_from_ms(value.closed_until_ms),
            closed_until_ms=value.closed_until_ms,
            status=safe_enum(SetupStatus, value.status),
            setup_type=value.setup_type,
            direction=safe_enum(Direction, value.direction),
            quality=value.quality,
            quality_score=value.quality_score,
            updated_at=utc_text(value.updated_at),
        )

    def setup_detail(self, value: SetupRecord) -> SetupDetail:
        if value.executable:
            raise ValueError("executable setups cannot be exposed")
        return SetupDetail(
            summary=self.setup_summary(value),
            confirmation_state=value.confirmation_state,
            reason_codes=list(value.reason_codes),
            warnings=list(value.warnings),
            invalidation_reasons=list(value.invalidation_reasons),
            strategy_status=value.strategy_status,
            risk_status=value.risk_status,
            paper_status=value.paper_status,
            hypothetical_entry=decimal_text(value.hypothetical_entry),
            hypothetical_stop=decimal_text(value.hypothetical_stop),
            hypothetical_target=decimal_text(value.hypothetical_target),
            planned_rr=decimal_text(value.planned_rr),
            executable=False,
        )

    def incident_summary(self, value: IncidentRecord) -> IncidentSummary:
        return IncidentSummary(
            incident_id=value.incident_id,
            status=safe_enum(IncidentStatus, value.status),
            severity=safe_enum(Severity, value.severity),
            source=value.source,
            title=value.title,
            symbol=value.symbol.upper() if value.symbol else None,
            opened_at=utc_text(value.opened_at),
            updated_at=utc_text(value.updated_at),
            resolved_at=utc_text(value.resolved_at) if value.resolved_at else None,
        )

    def incident_detail(self, value: IncidentRecord) -> IncidentDetail:
        return IncidentDetail(
            summary=self.incident_summary(value),
            safe_description=value.safe_description,
            reason_code=value.reason_code,
            timeframe=value.timeframe,
            closed_until=utc_from_ms(value.closed_until_ms) if value.closed_until_ms is not None else None,
            closed_until_ms=value.closed_until_ms,
        )

    def run(self, value: RunRecord) -> PipelineRunSummary:
        mapped = value.status
        if mapped.startswith("SKIPPED_"):
            mapped = "SKIPPED"
        elif mapped in {"RESERVED", "CHECKING_FRESHNESS"}:
            mapped = "PENDING"
        return PipelineRunSummary(
            run_id=value.run_id,
            symbol=value.symbol.upper(),
            primary_timeframe=value.primary_timeframe,
            closed_until=utc_from_ms(value.closed_until_ms),
            closed_until_ms=value.closed_until_ms,
            status=safe_enum(PipelineStatus, mapped),
            attempt_count=max(0, value.attempt_count),
            result_count=max(0, value.result_count),
        )
