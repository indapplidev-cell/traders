# Read-only API dependency contract

`pyproject.toml` is the canonical declaration of direct project dependencies.
The release/test contract is the resolved, hash-locked set:

- `api-runtime.lock.txt`: runtime direct and transitive third-party packages;
- `api-dev.lock.txt`: the complete runtime set plus test/dev packages;
- `lock-tools.txt`: `pip-tools==7.5.2` and its exact tool dependencies.

The locks reproduce the successful API retest package set at source commit
`3f3444fb0691854c89a47c7e20816d92daedff6e`. They target CPython 3.11 and
are verified on Windows and on Linux `python:3.11-slim`, the production base
platform declared by `Dockerfile`. Every distribution is pinned with `==` and
covered by one or more SHA256 hashes.

The API server is the exact direct runtime dependency `uvicorn==0.51.0`.
This version adds only Uvicorn and its required `click` dependency to the
previously passing runtime set; the already locked `h11==0.16.0` is reused.
Existing package versions, including `fastapi==0.116.1`, must not drift.

## Install

Create a fresh environment outside the repository. Do not install into a
project or user environment.

Runtime:

```powershell
python -m pip install --disable-pip-version-check --no-input --require-hashes -r requirements/api-runtime.lock.txt
python -m pip install --disable-pip-version-check --no-input --no-deps .
python -m pip check
python scripts/verify_api_dependency_lock.py
traders-readonly-api --help
```

Development and tests:

```powershell
python -m pip install --disable-pip-version-check --no-input --require-hashes -r requirements/api-dev.lock.txt
python -m pip install --disable-pip-version-check --no-input --no-deps -e .
python -m pip check
python scripts/verify_api_dependency_lock.py
```

`pip install ".[dev]"` is not a reproducible release/test contract.

## Controlled regeneration

Never edit a lock file by hand and never use `pip-compile --upgrade`. Start
from an approved passing environment and export separate exact runtime and dev
constraints outside the repository. Exclude the local project, editable paths,
`pip`, `setuptools`, and temporary tooling. Review every version difference
against the approved passing set.

Create a task-owned CPython 3.11 tool environment and install the locked
generator:

```powershell
python -m venv <TASK_RUNTIME>\lock_tool_venv
<TASK_RUNTIME>\lock_tool_venv\Scripts\python.exe -m pip install --require-hashes -r requirements/lock-tools.txt
```

Generate lock bodies from `pyproject.toml`:

```powershell
<TASK_RUNTIME>\lock_tool_venv\Scripts\pip-compile.exe pyproject.toml --output-file <TASK_RUNTIME>\api-runtime.body.txt --constraint <PASSING_RUNTIME_CONSTRAINTS> --generate-hashes --resolver backtracking --no-emit-index-url --no-header --no-annotate --strip-extras
<TASK_RUNTIME>\lock_tool_venv\Scripts\pip-compile.exe pyproject.toml --extra dev --output-file <TASK_RUNTIME>\api-dev.body.txt --constraint <PASSING_DEV_CONSTRAINTS> --generate-hashes --resolver backtracking --no-emit-index-url --no-header --no-annotate --strip-extras
```

In the same controlled generation script, prepend the deterministic six-line
header used by the checked-in files. Set its source commit, target, exact
generator version, normalized command, and UTC generation date explicitly.
Write UTF-8 with LF line endings, then atomically replace the lock files. Run:

```powershell
python scripts/verify_api_dependency_lock.py
git diff --check
```

Perform two independent fresh installs with `--require-hashes`, compare
normalized `pip freeze --all` output, run `pip check`, the focused API gate,
the safe regression gate, and the Linux production-platform smoke. A lock
update is rejected if FastAPI differs from `0.116.1` or any material package
differs from the approved passing set without an explicit reviewed exception.
