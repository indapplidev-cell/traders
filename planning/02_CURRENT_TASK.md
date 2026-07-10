# Current Task

## Этап

BOOK-L1-00 — Stop Growth and Confirm New Priority

## Цель этапа

Остановить разрастание старой ML38.10 diagnostic-ветки и зафиксировать новый главный приоритет проекта:

> BOOK-L1 Market Reader

## Что нужно подтвердить

Первый слой проекта должен делать:

- графико-технический анализ свечей;
- построение тренда;
- определение структуры рынка;
- определение структуры рынка;
- классификацию режима рынка: `UP / DOWN / FLAT / UNKNOWN`;
- объяснение результата через `reason_codes`.

## Что запрещено в этом этапе

На этом этапе нельзя:

- запускать quick-quality;
- запускать heavy wrappers;
- создавать новые ML38.10 diagnostics;
- менять label policy;
- менять class weights;
- менять training objective;
- утверждать наличие tradable edge;
- добавлять торговые сигналы LONG/SHORT;
- подключать результат к runtime execution.

## Ожидаемый результат этапа

После BOOK-L1-00 в проекте должен быть зафиксирован новый курс:

> сначала Market Reader, потом setup evaluation, потом edge validation.
