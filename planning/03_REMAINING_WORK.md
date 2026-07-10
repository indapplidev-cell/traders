# Remaining Work

## Новый порядок работ

### BOOK-L1-00 — Stop Growth and Confirm New Priority

Зафиксировать новый курс проекта и остановить разрастание старой ML38.10 diagnostic-ветки.

Статус: current.

### BOOK-L1-01 — Planning Cleanup and Project Control

Привести `planning/` к чистой структуре:

- общий план;
- текущий статус;
- текущая задача;
- оставшаяся работа;
- книги;
- ручной workflow.

### BOOK-L1-02 — Market Analysis Schemas

Создать базовые схемы результата анализа рынка:

- `MarketRegime`;
- `DirectionalBias`;
- `TrendStrength`;
- `MarketAnalysisResult`;
- `reason_codes`;
- `trade_signal = NOT_EVALUATED`.

### BOOK-L1-03 — Candle Window

Создать слой работы с окном свечей:

- последние N свечей;
- open/high/low/close/volume;
- защита от пустых данных;
- защита от lookahead.

### BOOK-L1-04 — Candle Morphology

Добавить признаки свечей:

- тело свечи;
- верхняя тень;
- нижняя тень;
- диапазон;
- bullish/bearish candle;
- doji-like candle;
- strong body candle.

### BOOK-L1-05 — Swing High / Swing Low Detector

Научить систему находить локальные максимумы и минимумы.

Это основа для построения тренда.

### BOOK-L1-06 — Trend Structure Analyzer

Определять:

- higher highs;
- higher lows;
- lower highs;
- lower lows;
- восходящую структуру;
- нисходящую структуру;
- сломанную структуру.

### BOOK-L1-07 — Range Structure Analyzer

Определять боковой рынок:

- диапазон;
- верхняя граница;
- нижняя граница;
- частые возвраты внутрь диапазона;
- слабое продолжение после пробоев.

### BOOK-L1-08 — Breakout / Retest Analyzer

Определять:

- пробой;
- ретест;
- ложный пробой;
- возврат в диапазон;
- follow-through после пробоя.

### BOOK-L1-09 — BookDrivenMarketAnalyzer V1

Объединить анализаторы в первый рабочий слой.

Выход:

- `UP`;
- `DOWN`;
- `FLAT`;
- `UNKNOWN`;
- `confidence`;
- `trend_strength`;
- `reason_codes`.


### BOOK-L1-10 — CLI Preview

Сделать команду предпросмотра анализа рынка по символу и таймфрейму.

Пример будущего результата:

```json
{
  "symbol": "SOLUSDT",
  "interval": "15m",
  "market_regime": "UP",
  "directional_bias": "BULLISH",
  "trend_strength": "MODERATE",
  "trade_signal": "NOT_EVALUATED",
  "safe_for_runtime_trading": false,
  "reason_codes": [
    "HIGHER_HIGHS_HIGHER_LOWS",
    "PRICE_ABOVE_EMA",
    "BULLISH_FOLLOW_THROUGH"
  ]
}
```
