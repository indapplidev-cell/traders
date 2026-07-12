# ENGINE_TREND — мастер-план нового book-based L1-модуля

## Статус документа

```text
MASTER PLAN
```

Этот документ фиксирует новый основной план для слоя `BOOK-L1`.

От этого плана не отступать без отдельного явного решения пользователя.

Периодически сверяться с этим документом перед началом новых этапов.

---

## Решение по названию модуля

Новый модуль определения тренда и настроения рынка называется:

```text
engine_trend
```

Рабочее назначение:

```text
engine_trend = book-based engine for trend and market mood reading
```

Русский смысл:

```text
engine_trend — движок чтения тренда и состояния рынка
```

---

## Главная цель engine_trend

`engine_trend` должен получать набор свечей за выбранный период и определять состояние рынка на этом периоде:

```text
UP
DOWN
FLAT
UNKNOWN
```

Ключевой принцип:

```text
один выбранный период = один входной набор свечей = один честный анализ этого периода
```

L1 не должен подбирать окно, чтобы получить нужный ответ.

Примеры:

```text
если передали свечи за 1 час — engine_trend анализирует этот 1 час;
если передали свечи за 1 день — engine_trend анализирует этот день;
если передали свечи за 1 год — engine_trend анализирует этот год.
```

Правильная логика:

```text
выбранный период
→ набор свечей
→ единая book-based методология
→ UP / DOWN / FLAT / UNKNOWN
→ объяснение через evidence и reason_codes
```

Неправильная логика:

```text
поменять window_size,
пока не появится нужный режим
```

---

## Главный архитектурный выбор

Не переписывать весь проект с нуля.

Оставить существующую инфраструктуру:

```text
BOOK-DATA
существующие свечные данные
CLI
JSON exports
BOOK-L2
FLAT_CONTEXT
JSON consumer
API readiness
reports
planning
tests
terminal guide
```

Но новый L1 market-reading core писать чисто внутри существующего проекта:

```text
app/market_reader/engine_trend/
```

Старый L1 не удалять сразу.

Старый L1 временно остаётся:

```text
baseline
reference
fallback for comparison
```

Новый `engine_trend` должен быть внедрён параллельно, проверен, сравнен со старым L1 и только потом может заменить старую L1-логику.

---

## Запрещено

В рамках `engine_trend` запрещено:

```text
торговые сигналы
BUY
SELL
LONG
SHORT
ENTRY
EXIT
stop-loss
take-profit
position sizing
edge validation
runtime trading
Binance order execution
BOOK-L3
подбор окна ради нужного режима
изменение данных ради результата
lookahead
training labels
class weights
training objective changes
```

`engine_trend` — это не торговый робот.

`engine_trend` — это аналитический слой чтения рынка.

---

## Источники знаний

`engine_trend` строится на трёх книгах:

```text
1. Steve Nison — Japanese Candlestick Charting Techniques /
   «Японские свечи: графический анализ финансовых рынков»

2. Т. М. Алтунина — «Основы технического анализа финансовых рынков»

3. Jack Schwager — «Технический анализ. Полный курс»
```

Все три книги использовать максимально.

Но использовать их правильно:

```text
книжная идея
→ формализуемый признак
→ evidence
→ reason_code
→ вклад в regime
```

Не превращать книжные паттерны в сделки.

---

# Роль каждой книги

## 1. Нисон

Роль:

```text
свечной контекст
```

Что даёт:

```text
тело свечи
верхняя тень
нижняя тень
close near high / low
doji
spinning top
hammer
hanging man
engulfing
dark cloud cover
piercing pattern
morning/evening star
shooting star
harami
tweezers
windows/gaps
continuation patterns
candle clusters
свечи около уровней
подтверждение / follow-through
```

Зачем:

```text
чтобы engine_trend понимал силу/слабость внутри свечей и групп свечей
```

Главное правило Нисона для engine_trend:

```text
свеча без контекста не решает режим;
свеча + тренд + уровень + подтверждение = сильный evidence.
```

---

## 2. Алтунина

Роль:

```text
методологический каркас технического анализа
```

Что даёт:

```text
принципы технического анализа
OHLC-подготовка
тренд
импульс
коррекция
поддержка
сопротивление
визуальные модели
Фибоначчи как контекст коррекции
облегчённый Elliott context
EMA
Bollinger Bands
MACD
RSI
Stochastic
Momentum
ROC
объём
совмещение методов
```

Зачем:

```text
чтобы engine_trend был системным анализатором, а не набором разрозненных эвристик
```

Главное правило Алтуниной для engine_trend:

```text
анализ должен идти по структуре:
данные → тренд → импульс/коррекция → уровни → модели → индикаторы → confluence/conflict → режим
```

---

## 3. Швагер

Роль:

```text
практическая защита от ложных интерпретаций
```

Что даёт:

```text
HH/HL
LH/LL
trend lines
internal trend lines
trading ranges
support/resistance zones
breakout
retest
polarity flip
false breakout
bull trap
bear trap
failed signals
confirmation
follow-through
range return
pattern failure
quality audits
```

Зачем:

```text
чтобы engine_trend не путал шум, ложный пробой и субъективную модель с настоящим режимом рынка
```

Главное правило Швагера для engine_trend:

```text
без подтверждения не объявлять новый режим с высокой уверенностью.
```

---

# Целевой pipeline engine_trend

```text
Candles for selected period
  ↓
InputPeriodContract
  ↓
OHLCIntegrityCheck
  ↓
CandleMorphology
  ↓
NisonCandlestickContext
  ↓
SwingPointDetector
  ↓
SwingStructureAnalyzer
  ↓
TrendImpulseCorrectionAnalyzer
  ↓
SupportResistanceZoneAnalyzer
  ↓
RangeStructureAnalyzer
  ↓
BreakoutRetestAnalyzer
  ↓
FalseBreakoutAnalyzer
  ↓
IndicatorContextAnalyzer
  ↓
ConfluenceConflictAnalyzer
  ↓
BookEvidenceMatrix
  ↓
EngineTrendRegimeComposer
  ↓
EngineTrendResult
```

---

# Предлагаемая структура файлов

```text
app/market_reader/engine_trend/
  __init__.py

  schemas.py
  input_period.py
  ohlc_integrity.py

  candle_morphology.py
  nison_candlestick_context.py
  candle_cluster_context.py

  swing_points.py
  swing_structure.py
  impulse_correction.py

  support_resistance_zones.py
  range_structure.py
  breakout_retest.py
  false_breakout.py

  indicator_context.py
  confluence_conflict.py
  book_evidence_matrix.py

  regime_composer.py
  engine.py

  json_export.py
  cli_preview.py
  audit.py
```

Не обязательно создавать всё сразу.

Создавать поэтапно, но не менять общий план.

---

# Целевой результат engine_trend

Основной результат:

```text
EngineTrendResult
```

Минимальные поля:

```text
symbol
interval
period_start
period_end
candle_count

market_regime: UP / DOWN / FLAT / UNKNOWN
confidence: 0.0..1.0

trend_evidence
candlestick_evidence
range_evidence
level_evidence
breakout_evidence
false_breakout_evidence
indicator_evidence
confluence_evidence

book_evidence:
  nison
  altunina
  schwager

reason_codes
warnings
errors

trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
```

---

# Как engine_trend должен определять режим

## UP

`engine_trend` выдаёт `UP`, если есть несколько согласованных признаков:

```text
HH/HL
импульсы вверх сильнее коррекций
поддержки удерживаются
сопротивления пробиваются
бывшее сопротивление становится поддержкой
пробой подтверждён follow-through / retest
свечной контекст поддерживает рост
индикаторы не конфликтуют
нет bull trap / false breakout
```

Примеры reason_codes:

```text
HIGHER_HIGHS_HIGHER_LOWS
BULLISH_IMPULSE_DOMINANT
RESISTANCE_TURNED_SUPPORT
BULLISH_RANGE_BREAKOUT
BREAKOUT_FOLLOW_THROUGH_CONFIRMED
BULLISH_BODY_DOMINANCE
METHOD_CONFLUENCE_DETECTED
```

---

## DOWN

`engine_trend` выдаёт `DOWN`, если есть несколько согласованных признаков:

```text
LH/LL
импульсы вниз сильнее отскоков
сопротивления удерживаются
поддержки пробиваются
бывшая поддержка становится сопротивлением
breakdown подтверждён follow-through / retest
свечной контекст поддерживает снижение
индикаторы не конфликтуют
нет bear trap / false breakdown
```

Примеры reason_codes:

```text
LOWER_HIGHS_LOWER_LOWS
BEARISH_IMPULSE_DOMINANT
SUPPORT_TURNED_RESISTANCE
BEARISH_RANGE_BREAKDOWN
BREAKOUT_FOLLOW_THROUGH_CONFIRMED
BEARISH_BODY_DOMINANCE
METHOD_CONFLUENCE_DETECTED
```

---

## FLAT

`engine_trend` выдаёт `FLAT`, если есть осознанная боковая структура:

```text
нет устойчивой HH/HL или LH/LL структуры
есть торговый диапазон
верхняя граница удерживается
нижняя граница удерживается
пробои возвращаются внутрь
много overlap / small bodies / doji
EMA плоская или цена часто пересекает средние
нет направленного follow-through
ложные пробои усиливают range context
```

Примеры reason_codes:

```text
TRADING_RANGE_DETECTED
RANGE_UPPER_BOUNDARY_HELD
RANGE_LOWER_BOUNDARY_HELD
PRICE_RETURNED_TO_RANGE
DOJI_CLUSTER_FLAT_CONTEXT
EMA_FLAT
NO_FOLLOW_THROUGH
FALSE_BREAKOUT_UP
FALSE_BREAKOUT_DOWN
```

---

## UNKNOWN

`engine_trend` выдаёт `UNKNOWN`, если нельзя честно определить режим:

```text
данных мало
swing-точек мало
OHLC-данные невалидны
много конфликтов
уровни слишком широкие
range и trend признаки одновременно сильные
свечи противоречат структуре
есть data artifacts
confidence ниже минимального порога
```

Примеры reason_codes:

```text
INSUFFICIENT_SWING_POINTS
INVALID_OHLC_STRUCTURE
METHOD_CONFLICT_DETECTED
ZONE_OVERLAP_CONFLICT
GAP_MAY_BE_DATA_ARTIFACT
INSUFFICIENT_CONFLUENCE
```

---

# Правила confidence

Confidence не должен быть магическим числом.

Он должен быть decomposed:

```text
trend_score
range_score
candlestick_score
level_score
breakout_score
false_breakout_penalty
indicator_score
confluence_score
conflict_penalty
data_quality_penalty
```

Итоговая confidence должна объясняться.

Пример:

```json
{
  "confidence": 0.82,
  "confidence_decomposition": {
    "trend_score": 0.15,
    "range_score": 0.35,
    "candlestick_score": 0.18,
    "level_score": 0.22,
    "breakout_score": 0.0,
    "false_breakout_penalty": -0.05,
    "indicator_score": 0.08,
    "conflict_penalty": -0.01,
    "data_quality_penalty": 0.0
  }
}
```

---

# Старый L1

Старый L1 не удалять на ранних этапах.

Он остаётся:

```text
baseline/reference
```

Нужно уметь сравнить:

```text
old_l1_result
engine_trend_result
```

Сравнение нужно, чтобы понять:

```text
что изменилось;
почему изменилось;
улучшилось ли объяснение;
не потеряли ли мы важную функциональность;
не сломали ли L2 JSON/API chain.
```

---

# L2

L2 не должен переопределять режим.

L2 должен принимать результат `engine_trend` и объяснять контекст.

Правило:

```text
L1 / engine_trend определяет market_regime.
L2 интерпретирует и объясняет.
```

Для `FLAT`:

```text
engine_trend FLAT
→ L2 FLAT_CONTEXT
```

Для `UP/DOWN`:

```text
engine_trend UP/DOWN
→ L2 directional context, но без торгового сигнала
```

Для `UNKNOWN`:

```text
engine_trend UNKNOWN
→ L2 UNKNOWN / skip / fail-closed
```

---

# Этапы реализации

## ENGINE-TREND-00 — Plan Anchor

Цель:

```text
зафиксировать этот мастер-план в проекте
```

Ожидаемые файлы:

```text
planning/09_ENGINE_TREND_MASTER_PLAN.md
planning/02_CURRENT_TASK.md
planning/03_REMAINING_WORK.md
planning/04_BOOK_L1_MARKET_READER_PLAN.md
```

Результат:

```text
план сохранён;
название engine_trend зафиксировано;
следующие этапы идут только по этому плану.
```

---

## ENGINE-TREND-01 — Current L1 vs Book Matrix Audit

Цель:

```text
проверить текущий L1 против матрицы Нисон/Алтунина/Швагер
```

Ответить:

```text
что уже есть;
что частично;
чего нет;
какие reason_codes есть;
какие reason_codes отсутствуют;
почему текущий FLAT был выдан;
есть ли у него полноценное книжное объяснение.
```

Важно:

```text
не менять логику;
только audit/evidence.
```

---

## ENGINE-TREND-02 — Engine Trend Schemas and Input Contract

Цель:

```text
создать базовые схемы engine_trend и контракт входного периода
```

Добавить:

```text
EngineTrendRegime
EngineTrendResult
EngineTrendEvidence
BookEvidence
ConfidenceDecomposition
InputPeriod
OHLC validation contract
```

---

## ENGINE-TREND-03 — Nison Candle Morphology and Candlestick Context

Цель:

```text
внедрить свечной контекст Нисона
```

Добавить:

```text
candle body/shadow metrics
doji/spinning top
strong body
hammer/hanging-man context
engulfing context
dark cloud / piercing context
stars context
harami
tweezers
candle clusters
candle near levels hook
```

---

## ENGINE-TREND-04 — Altunina Technical Analysis Framework

Цель:

```text
внедрить методологический каркас Алтуниной
```

Добавить:

```text
trend direction
impulse/correction
support/resistance base
visual pattern context
indicator context hooks
method confluence/conflict basics
```

---

## ENGINE-TREND-05 — Schwager Practical Chart Logic

Цель:

```text
внедрить практическую защиту Швагера
```

Добавить:

```text
HH/HL and LH/LL confirmation
trading range
support/resistance zones
breakout/retest
polarity flip
false breakout
failed signals
confirmation/follow-through
```

---

## ENGINE-TREND-06 — Book Evidence Matrix

Цель:

```text
собрать evidence из трёх книг в единую матрицу
```

Результат:

```text
каждый вывод имеет source:
NISON / ALTUNINA / SCHWAGER
```

---

## ENGINE-TREND-07 — Book-Based Regime Composer

Цель:

```text
создать composer, который принимает evidence и выдаёт UP/DOWN/FLAT/UNKNOWN
```

Важно:

```text
не один признак решает режим;
режим выбирается через confluence/conflict;
confidence decomposed.
```

---

## ENGINE-TREND-08 — Engine Trend CLI Preview and JSON Export

Цель:

```text
добавить CLI preview и JSON export для engine_trend
```

Команда:

```powershell
python -m app.cli.commands engine-trend-preview
```

---

## ENGINE-TREND-09 — Old L1 vs Engine Trend Comparison

Цель:

```text
сравнить старый L1 и новый engine_trend на одинаковых свечах
```

Результат:

```text
old_l1_regime
engine_trend_regime
difference_reason
evidence_comparison
```

---

## ENGINE-TREND-10 — L2 Integration Review

Цель:

```text
проверить, что L2 корректно принимает результат engine_trend
```

Важно:

```text
L2 не должен переопределять режим.
```

---

## ENGINE-TREND-11 — Switch Candidate Review

Цель:

```text
решить, готов ли engine_trend заменить старый L1
```

До этого этапа старый L1 не удалять.

---

# Проверка каждого этапа

Каждый этап обязан проверять:

```text
git status before/after
py_compile
targeted tests
relevant BOOK-L1/L2/DATA tests
real smoke where applicable
JSON output
Markdown evidence
forbidden trading operations scan
L1/L2 runtime contract safety
git diff --cached --check
final git status clean
```

---

# Правило сверки

Перед каждым новым этапом нужно сверяться с этим документом и отвечать:

```text
какой пункт плана выполняется;
какие файлы должны появиться;
что запрещено менять;
какой результат считается PASS.
```

Если этап не вписывается в этот мастер-план, его не начинать без отдельного подтверждения пользователя.

---

# Финальный принцип

```text
engine_trend не торгует.
engine_trend читает рынок.
```

Он должен стать новым чистым book-based ядром L1, которое на любом выбранном периоде свечей честно определяет:

```text
UP
DOWN
FLAT
UNKNOWN
```

и объясняет это через знания из трёх книг:

```text
Нисон
Алтунина
Швагер
```

Не сигнал.

Не edge.

Не runtime execution.

Только чтение рынка.
