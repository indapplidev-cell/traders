# Инструкции проекта traders-ml

## Актуализация online_trader.md

`online_trader.md` является post-task snapshot доказанного состояния проекта.

Он не является:

- планом ожидаемого результата текущей незавершенной задачи;
- заменой Git history;
- заменой tests/evidence;
- источником собственного commit SHA.

Перед выполнением каждого входящего пользовательского промпта, относящегося к
проекту traders-ml, Codex обязан соблюдать следующий lifecycle.

### PHASE 1 — PRE-TASK READ

1. Прочитать `AGENTS.md`.
2. Прочитать корневой файл `online_trader.md`.
3. Сравнить новый промпт с доказанным состоянием в документе, фактическим Git,
   implementation/test/deployment/audit artifacts и применимым runtime state.
4. Определить текущие stage, blocker, next task и ограничения.
5. Не записывать текущую задачу как completed до ее фактического завершения и
   доказанного PASS.

### PHASE 2 — TASK EXECUTION

6. Выполнить разрешенные implementation/audit/deployment действия.
7. Завершить применимые к задаче tests, compile, canary, SQL corroboration и
   evidence.
8. Сформировать доказанный `FINAL_VERDICT`.

### PHASE 3 — PROJECT-STATE COMMIT

9. При наличии runtime/test/audit/project-state изменений создать commit,
   содержащий фактический результат задачи.
10. Получить полный SHA этого commit.
11. Использовать его как кандидата `STATUS_AS_OF_COMMIT`.

`STATUS_AS_OF_COMMIT` указывает на последний commit фактического состояния,
которое описывает документ. Обычно это implementation, audit-result,
integration или deployment/status integration commit. Это не commit самого
`online_trader.md`.

Если задача изменяет только `AGENTS.md`/`online_trader.md` и не меняет
фактическое состояние проекта, `STATUS_AS_OF_COMMIT` сохраняется равным
последнему доказанному project-state commit.

### PHASE 4 — FRESH STATE REREAD

12. После project-state commit повторно считать actual Git/runtime state.
13. Повторно проверить HEAD, remote, push, deployment, DB/Alembic, services,
    canary/soak и LIVE в применимом к задаче scope.
14. Не использовать как финальные значения, прочитанные только в начале задачи.

### PHASE 5 — STATUS RECONCILIATION

15. Обновить `online_trader.md` последним как post-task snapshot.
16. Перевести завершенную задачу в completed только при PASS.
17. Установить `CURRENT_STAGE` на следующий фактический этап.
18. При наличии runtime/test/audit изменений создать отдельный documentation
    reconciliation commit после project-state commit.

Минимальная последовательность commits для такой задачи:

1. project-state commit;
2. documentation reconciliation commit.

Пример:

```text
fix(market-data): clear recovered pair health errors
docs(project): reconcile recovered pair health reset status
```

Documentation commit должен идти последним. Чистая documentation-governance
задача может иметь один documentation commit, поскольку project state не
изменяется.

### PHASE 6 — FINAL VERIFICATION

19. Определить documentation commit через Git.
20. Проверить, что `online_trader.md` не пытается хранить его SHA.
21. Выполнить final consistency check.
22. Только после этого вывести финальный ответ.

### Self-reference-safe revision

`online_trader.md` обязан содержать:

```text
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md
```

Внутри файла запрещены собственные абсолютные SHA в полях:

```text
DOCUMENT_COMMIT = <absolute SHA>
ONLINE_TRADER_COMMIT = <absolute SHA>
CURRENT_DOCUMENT_SHA = <absolute SHA>
```

Фактический documentation commit разрешено указывать в `FINAL_DECISION.md`,
evidence и финальном ответе Codex, но не внутри `online_trader.md` как
собственный SHA.

### Динамические Git transport fields

Поля HEAD/ahead/behind/pushed быстро устаревают и не являются долговечным
архитектурным статусом. В `online_trader.md` разрешены только snapshot-поля с
явной временной семантикой:

```text
REMOTE_PRODUCTION_BASE_AT_RECONCILIATION
PUSH_STATE_AT_RECONCILIATION
RECONCILED_AT_UTC
```

Точные значения `LOCAL_HEAD`, `LOCAL_AHEAD`, `LOCAL_BEHIND`, `TAG_OBJECT`,
`REMOTE_HEAD_AFTER_PUSH` и `WORKTREE_STATUS` должны храниться в
`FINAL_DECISION.md`, deployment/audit evidence или финальном task handoff.

### Правила доказанного состояния

При каждой релевантной задаче определить, меняется ли хотя бы один параметр:

- список модулей;
- статус или процент модуля;
- архитектура или runtime integration;
- deployment, test или production acceptance status;
- текущий blocker;
- completed/current/upcoming stages;
- Git baseline/head/tag или Docker image;
- Alembic version;
- soak/canary/audit status;
- LIVE readiness или safety restrictions.

Если изменения доказаны, актуализировать `online_trader.md` в рамках той же
задачи. Если задача не меняет состояние проекта, не переписывать документ без
необходимости, кроме явно разрешенной documentation-governance correction.

Документ должен отражать только доказанное состояние:

- design/contract != implementation;
- implementation != integration;
- integration != deployment;
- deployment != production acceptance;
- canary != 72h soak;
- blocked soak != active soak;
- local commit != remote production state.

Нельзя повышать процент только потому, что создан файл, интерфейс, тест или
документ. Если фактов недостаточно, сохранить процент и уточнить описание.

При появлении нового модуля добавить его в таблицу с названием, процентом,
фактическим статусом, ограничениями и следующим шагом. При изменении модуля
обновить описание реализации, regression/validation и deployment/production
status.

Если пользовательский промпт конфликтует с фактическим состоянием, использовать
доказанное состояние и явно зафиксировать расхождение.

`online_trader.md` является единым status-документом, но не заменяет source
code, tests, migrations, deployment evidence, production DB и Git history.

### Final reconciliation gate

Перед завершением каждого значимого задания проверить:

- текущая задача не названа completed без PASS;
- `CURRENT_STAGE` указывает на следующий этап;
- blocker соответствует post-task состоянию;
- SOAK не назван active, если не запущен;
- deployment не назван accepted без canary;
- local commit не назван remote state;
- document self SHA отсутствует;
- `STATUS_AS_OF_COMMIT` существует в Git;
- `STATUS_AS_OF_COMMIT` является ancestor documentation commit;
- `DOCUMENT_REVISION = SELF`;
- все динамические Git значения имеют суффикс или явное описание
  `AT_RECONCILIATION`;
- `online_trader.md` включен в `FILES_CHANGED`, если был обновлен.
