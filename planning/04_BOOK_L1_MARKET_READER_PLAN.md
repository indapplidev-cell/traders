# BOOK-L1 Market Reader Plan

## Короткое название

BOOK-L1 Market Reader

## Русское название

Слой 1 — Чтение рынка

## Главная цель

Построить первый слой графико-технического анализа рынка.

Слой должен читать историю свечей и определять:

- рынок восходящий;
- рынок нисходящий;
- рынок боковой;
- структура неясная.

## Входные данные

История свечей:

- symbol;
- interval;
- timestamp;
- open;
- high;
- low;
- close;
- volume.

## Основной pipeline

```text
Candles
  ↓
CandleWindow
  ↓
CandleMorphology
  ↓
SwingHighSwingLowDetector
  ↓
TrendStructureAnalyzer
  ↓
RangeStructureAnalyzer
  ↓
BreakoutRetestAnalyzer
  ↓
BookDrivenMarketAnalyzer
  ↓
MarketAnalysisResult
```

## Что должен определить слой

### UP

Признаки:

- higher highs;
- higher lows;
- цена чаще закрывается выше средней;
- откаты не ломают структуру;
- после пробоев есть продолжение;
- бычьи свечи сильнее медвежьих.

### DOWN

Признаки:

- lower highs;
- lower lows;
- цена чаще закрывается ниже средней;
- отскоки слабые;
- после пробоев вниз есть продолжение;
- медвежьи свечи сильнее бычьих.

### FLAT

Признаки:

- нет устойчивых higher highs / lower lows;
- цена ходит между верхней и нижней границей;
- много перекрывающихся свечей;
- пробои часто возвращаются обратно;
- EMA почти горизонтальная;
- движение без продолжения.

### UNKNOWN

Используется, если данных мало или признаки конфликтуют.

## Важное ограничение

BOOK-L1 Market Reader не должен давать торговый сигнал.

Он не говорит:

- buy;
- sell;
- long;
- short;
- enter;
- exit.

Он говорит только:

- структура рынка;
- режим рынка;
- объяснение.

## Целевой результат

```json
{
  "market_regime": "UP",
  "directional_bias": "BULLISH",
  "confidence": 0.71,
  "trend_strength": "MODERATE",
  "trade_signal": "NOT_EVALUATED",
  "safe_for_runtime_trading": false,
  "reason_codes": [
    "HIGHER_HIGHS_HIGHER_LOWS",
    "PRICE_ABOVE_EMA",
    "EMA_SLOPE_UP",
    "SHALLOW_PULLBACK",
    "BULLISH_FOLLOW_THROUGH"
  ]
}
```

## Почему это первый слой

Потому что невозможно честно проверять торговый edge, пока система не умеет стабильно читать рынок.

Сначала:

> что происходит на рынке?

Потом:

> есть ли setup?

И только потом:

> есть ли edge?
