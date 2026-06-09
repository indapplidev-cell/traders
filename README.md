# traders-ml

`traders-ml` is an independent ML service for the trading project. It stores market history, builds features and labels, assembles train/validation/test datasets, trains PyTorch MLP models, runs diagnostics, serves prediction and replay flows, and keeps model artifacts and registry entries inside this project.

## Stack

- Python
- FastAPI
- Typer
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- PyTorch
- pytest
- Docker
- docker-compose

## PostgreSQL

Start PostgreSQL from the project root:

```bash
docker-compose up -d
```

Default local database URL:

```text
postgresql+psycopg://traders_ml:traders_ml@localhost:5433/traders_ml
```

## Migrations

Apply schema migrations:

```bash
alembic upgrade head
```

## Full Pipeline

Load candles:

```bash
python -m app.cli.commands load-candles --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31
```

Check candle gaps:

```bash
python -m app.cli.commands check-candle-gaps --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31
```

Build features:

```bash
python -m app.cli.commands build-features --symbol BTCUSDT --interval 15m --feature-version fv1
```

Build labels:

```bash
python -m app.cli.commands build-labels --symbol BTCUSDT --interval 15m --horizon-candles 8 --label-version lv1
```

Build dataset:

```bash
python -m app.cli.commands build-dataset --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
```

Evaluate baselines:

```bash
python -m app.cli.commands evaluate-baselines --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
```

Run dataset diagnostics:

```bash
python -m app.cli.commands dataset-diagnostics --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
```

Run overfit sanity check:

```bash
python -m app.cli.commands overfit-check --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --rows 256 --epochs 100
```

Train a model:

```bash
python -m app.cli.commands train --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --model-name candle_mlp --epochs 20 --learning-rate 0.001 --weight-decay 0.0001 --train-end 2025-03-01 --validation-end 2025-03-16
```

List registered models:

```bash
python -m app.cli.commands model-list
```

Activate a model:

```bash
python -m app.cli.commands model-activate --model-version <MODEL_VERSION>
```

Check model diagnostics:

```bash
python -m app.cli.commands model-diagnostics --model-version <MODEL_VERSION> --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
```

Compare baselines and registered models:

```bash
python -m app.cli.commands compare-models --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
```

Check one sample prediction:

```bash
python -m app.cli.commands predict-sample --symbol BTCUSDT --interval 15m --horizon-candles 8 --limit 220
```

Run historical replay:

```bash
python -m app.cli.commands replay --model-version <MODEL_VERSION> --symbol BTCUSDT --interval 15m --start-date 2025-03-16 --end-date 2025-03-31 --horizon-candles 8
```

## API

Health endpoint:

```text
GET /health
```

Prediction endpoint:

```text
POST /predict
```

Model registry endpoints:

```text
GET /models
POST /models/activate
```

Replay sessions endpoint:

```text
GET /replay/sessions
```

## Model Training Notes

- Direction loss supports class weights by default.
- Disable class weights only if you explicitly want to compare against the unweighted setup:

```bash
python -m app.cli.commands train --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --model-name candle_mlp --disable-class-weights
```

- Artifacts are saved under `artifacts/models/<MODEL_VERSION>/`.
- Registry metadata is stored in PostgreSQL table `ml_model_versions`.

## Weak Metrics Interpretation

Weak metrics do not automatically mean the infrastructure is broken. Check them in this order:

1. Compare the trained model against baseline reports in `reports/baseline_*.json`.
2. Open `reports/model_diagnostics_<MODEL_VERSION>.json` and verify whether prediction collapse was detected.
3. Run `overfit-check`. If the model cannot beat random baseline on a tiny train subset, suspect a bug in features, labels, loss wiring, or the training loop.
4. Inspect dataset label distribution in `reports/dataset_diagnostics_*.json`.
5. If the model is weaker than the best baseline, do not activate it automatically.

## Required Command Block

```bash
alembic upgrade head

python -m app.cli.commands load-candles --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31

python -m app.cli.commands check-candle-gaps --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31

python -m app.cli.commands build-features --symbol BTCUSDT --interval 15m --feature-version fv1

python -m app.cli.commands build-labels --symbol BTCUSDT --interval 15m --horizon-candles 8 --label-version lv1

python -m app.cli.commands build-dataset --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16

python -m app.cli.commands train --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --model-name candle_mlp --epochs 20 --train-end 2025-03-01 --validation-end 2025-03-16

python -m app.cli.commands model-list

python -m app.cli.commands model-activate --model-version <MODEL_VERSION>

python -m app.cli.commands predict-sample --symbol BTCUSDT --interval 15m --horizon-candles 8 --limit 220

python -m app.cli.commands replay --model-version <MODEL_VERSION> --symbol BTCUSDT --interval 15m --start-date 2025-03-16 --end-date 2025-03-31 --horizon-candles 8
```
