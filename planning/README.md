# traders-ml planning

Эта папка предназначена только для проектного планирования.

Здесь должны храниться:

- общий план проекта;
- текущий статус;
- текущая задача;
- список оставшейся работы;
- план BOOK-L1 Market Reader;
- описание книг по анализу рынка;
- правила ручной работы.

В этой папке не должны храниться:

- Python-скрипты;
- временные run-файлы;
- snapshot-файлы для ChatGPT/Codex;
- ZIP-архивы;
- runtime-логи;
- большие диагностические выгрузки.

PDF-книги лежат локально в `planning/books/` и не добавляются в Git.

- BOOK-L1 Market Reader: read-only pipeline, CLI preview, real DB smoke report, and API/service response contract are completed through BOOK-L1-14.
- BOOK-L1-23: terminal command guide is available through `python -m app.cli.commands book-l1-guide`; terminal output is for humans, JSON export is for API, and runtime Markdown export is not used as working output.
