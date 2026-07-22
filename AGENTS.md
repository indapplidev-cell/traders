# Инструкции проекта traders-ml

## Актуализация online_trader.md

Перед выполнением каждого входящего пользовательского промпта,
относящегося к проекту traders-ml, Codex обязан:

1. Прочитать корневой файл `online_trader.md`.

2. Сравнить новый промпт:
   - с текущим содержимым `online_trader.md`;
   - с фактическим состоянием Git;
   - с результатами выполняемой задачи;
   - с implementation/test/deployment/audit artifacts.

3. Определить, меняет ли задача хотя бы один параметр:
   - список модулей;
   - статус или процент модуля;
   - архитектуру;
   - runtime integration;
   - deployment status;
   - test status;
   - production acceptance;
   - текущий blocker;
   - завершенные, текущие и предстоящие стадии;
   - Git baseline/head/tag;
   - Docker image;
   - Alembic version;
   - soak/canary/audit status;
   - LIVE readiness;
   - safety restrictions.

4. Если изменения обнаружены, Codex обязан в рамках той же задачи
   актуализировать `online_trader.md`.

5. Обновление должно отражать только доказанное состояние:
   - design/contract != implementation;
   - implementation != integration;
   - integration != deployment;
   - deployment != production acceptance;
   - canary != 72h soak;
   - blocked soak != active soak;
   - local commit != remote production state.

6. Нельзя повышать процент только потому, что создан новый файл,
   интерфейс, тест или документ.

7. При завершении, блокировке или изменении очередности этапов обновлять:
   - current stage;
   - completed/current/upcoming stages;
   - main blocker;
   - next recommended task;
   - проценты при наличии доказательств.

8. При появлении нового модуля добавлять его в таблицу с:
   - названием;
   - процентом;
   - фактическим статусом;
   - ограничениями;
   - следующим шагом.

9. При изменении существующего модуля обновлять:
   - процент;
   - описание реализованного;
   - regression/validation status;
   - deployment/production status.

10. Если задача не меняет состояние проекта, не переписывать
    `online_trader.md` без необходимости.

11. Перед завершением каждого значимого задания выполнять final status
    reconciliation:
    - сравнить фактический результат с `online_trader.md`;
    - обновить файл при расхождении;
    - проверить отсутствие противоречий;
    - включить `online_trader.md` в `FILES_CHANGED`.

12. Если фактов недостаточно для изменения процента, сохранить старый
    процент и добавить уточнение в описание.

13. Если пользовательский промпт конфликтует с фактическим состоянием,
    использовать доказанное состояние и явно зафиксировать расхождение.

14. `online_trader.md` является единым status-документом, но не заменяет:
    source code, tests, migrations, deployment evidence, production DB
    и Git history.
