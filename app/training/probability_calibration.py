from dataclasses import dataclass
from typing import Any, Iterable

import torch
import torch.nn.functional as F


DEFAULT_TEMPERATURE_GRID: tuple[float, ...] = (
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    1.00,
    1.10,
    1.25,
    1.50,
    1.75,
    2.00,
)


@dataclass(slots=True)
class DirectionTemperatureReport:
    """Результат подбора temperature scaling для direction probabilities."""

    enabled: bool
    selected_temperature: float
    raw_temperature: float
    raw_nll: float | None
    selected_nll: float | None
    raw_brier: float | None
    selected_brier: float | None
    candidate_temperatures: list[dict[str, float]]
    validation_rows: int
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "selected_temperature": self.selected_temperature,
            "raw_temperature": self.raw_temperature,
            "raw_nll": self.raw_nll,
            "selected_nll": self.selected_nll,
            "raw_brier": self.raw_brier,
            "selected_brier": self.selected_brier,
            "candidate_temperatures": list(self.candidate_temperatures),
            "validation_rows": self.validation_rows,
            "reason": self.reason,
        }


def softmax_with_temperature(logits: torch.Tensor, temperature: float | None = None) -> torch.Tensor:
    """Softmax с temperature scaling.

    temperature < 1.0 делает распределение острее;
    temperature > 1.0 делает распределение мягче;
    temperature = 1.0 оставляет raw softmax.
    """

    safe_temperature = float(temperature or 1.0)
    if safe_temperature <= 0:
        safe_temperature = 1.0
    return torch.softmax(logits / safe_temperature, dim=1)


def fit_direction_temperature_from_logits(
    logits: torch.Tensor,
    targets: torch.Tensor,
    candidate_temperatures: Iterable[float] = DEFAULT_TEMPERATURE_GRID,
) -> DirectionTemperatureReport:
    """Подбирает direction temperature по validation NLL.

    Это post-hoc calibration. Она не меняет веса модели и не смягчает gates.
    """

    if logits.shape[0] == 0 or targets.shape[0] == 0:
        return DirectionTemperatureReport(
            enabled=False,
            selected_temperature=1.0,
            raw_temperature=1.0,
            raw_nll=None,
            selected_nll=None,
            raw_brier=None,
            selected_brier=None,
            candidate_temperatures=[],
            validation_rows=0,
            reason="empty_validation_dataset",
        )

    logits = logits.detach()
    targets = targets.detach().long()
    raw_probabilities = softmax_with_temperature(logits, 1.0)
    raw_nll = float(F.cross_entropy(logits, targets).detach().item())
    raw_brier = _multiclass_brier(raw_probabilities, targets)

    rows: list[dict[str, float]] = []
    for temperature in candidate_temperatures:
        temp = float(temperature)
        if temp <= 0:
            continue
        probabilities = softmax_with_temperature(logits, temp)
        nll = float(F.cross_entropy(logits / temp, targets).detach().item())
        brier = _multiclass_brier(probabilities, targets)
        confidence_stats = probability_separation_stats(probabilities)
        rows.append(
            {
                "temperature": temp,
                "nll": nll,
                "brier": brier,
                "max_prob_q50": confidence_stats["max_prob_q50"],
                "max_prob_q90": confidence_stats["max_prob_q90"],
                "margin_q50": confidence_stats["margin_q50"],
                "rows_above_045_ratio": confidence_stats["rows_above_045_ratio"],
            }
        )

    if not rows:
        return DirectionTemperatureReport(
            enabled=False,
            selected_temperature=1.0,
            raw_temperature=1.0,
            raw_nll=raw_nll,
            selected_nll=raw_nll,
            raw_brier=raw_brier,
            selected_brier=raw_brier,
            candidate_temperatures=[],
            validation_rows=int(logits.shape[0]),
            reason="no_valid_temperature_candidates",
        )

    # Основной критерий — NLL. При равенстве предпочитаем меньшую температуру,
    # потому что текущая проблема проекта — underconfidence/collapse.
    best = min(rows, key=lambda item: (item["nll"], item["temperature"]))
    return DirectionTemperatureReport(
        enabled=True,
        selected_temperature=float(best["temperature"]),
        raw_temperature=1.0,
        raw_nll=raw_nll,
        selected_nll=float(best["nll"]),
        raw_brier=raw_brier,
        selected_brier=float(best["brier"]),
        candidate_temperatures=rows,
        validation_rows=int(logits.shape[0]),
        reason=None,
    )


def fit_direction_temperature_for_model(
    model: torch.nn.Module,
    validation_dataset: dict[str, torch.Tensor],
    candidate_temperatures: Iterable[float] = DEFAULT_TEMPERATURE_GRID,
) -> DirectionTemperatureReport:
    """Подбирает temperature по validation dataset."""

    if validation_dataset["features"].shape[0] == 0:
        return fit_direction_temperature_from_logits(
            logits=torch.zeros((0, 3), dtype=torch.float32),
            targets=torch.zeros((0,), dtype=torch.long),
            candidate_temperatures=candidate_temperatures,
        )

    model.eval()
    with torch.no_grad():
        outputs = model(validation_dataset["features"])
        logits = outputs["direction_logits"]
    return fit_direction_temperature_from_logits(
        logits=logits,
        targets=validation_dataset["direction_target"],
        candidate_temperatures=candidate_temperatures,
    )


def direction_temperature_from_metadata(
    training_config: dict[str, Any] | None,
    metrics: dict[str, Any] | None = None,
) -> float:
    """Достаёт выбранную temperature из artifact metadata."""

    training_config = training_config or {}
    metrics = metrics or {}

    for payload in (
        training_config.get("probability_calibration"),
        metrics.get("probability_calibration"),
    ):
        if isinstance(payload, dict):
            value = payload.get("selected_temperature") or payload.get("direction_temperature")
            if value is not None:
                try:
                    temperature = float(value)
                    return temperature if temperature > 0 else 1.0
                except (TypeError, ValueError):
                    pass
    return 1.0


def probability_separation_stats(probabilities: torch.Tensor) -> dict[str, float]:
    """Считает компактные показатели уверенности по probability matrix."""

    if probabilities.shape[0] == 0:
        return {
            "max_prob_q50": 0.0,
            "max_prob_q90": 0.0,
            "margin_q50": 0.0,
            "margin_q90": 0.0,
            "rows_above_045_ratio": 0.0,
            "rows_above_050_ratio": 0.0,
        }

    sorted_probabilities = torch.sort(probabilities, dim=1, descending=True).values
    max_prob = sorted_probabilities[:, 0]
    margin = sorted_probabilities[:, 0] - sorted_probabilities[:, 1]

    return {
        "max_prob_q50": float(torch.quantile(max_prob, 0.50).detach().item()),
        "max_prob_q90": float(torch.quantile(max_prob, 0.90).detach().item()),
        "margin_q50": float(torch.quantile(margin, 0.50).detach().item()),
        "margin_q90": float(torch.quantile(margin, 0.90).detach().item()),
        "rows_above_045_ratio": float((max_prob >= 0.45).float().mean().detach().item()),
        "rows_above_050_ratio": float((max_prob >= 0.50).float().mean().detach().item()),
    }


def _multiclass_brier(probabilities: torch.Tensor, targets: torch.Tensor) -> float:
    target_one_hot = F.one_hot(targets.long(), num_classes=probabilities.shape[1]).float()
    return float(torch.mean(torch.sum((probabilities - target_one_hot) ** 2, dim=1)).detach().item())
