# ENGINE-TREND-13 — Acceptance Commands

Run from the repository root. The DB URL must be supplied at runtime through one of `TRADERS_ML_DATABASE_URL`, `TRADERS_ML_POSTGRES_URL`, `DATABASE_URL`, or `POSTGRES_URL`. Do not commit the real DB URL.

## Availability

```powershell
python -m app.market_reader.engine_trend.db_cli_preview --availability
```

## BTCUSDT 15m

```powershell
python -m app.market_reader.engine_trend.db_cli_preview `
  --symbol BTCUSDT `
  --interval 15m `
  --max-candles 96 `
  --output reports\engine_trend\db_cli_preview\btcusdt_15m_result.json `
  --preview-output reports\engine_trend\db_cli_preview\btcusdt_15m_preview.json
```

## ETHUSDT 15m

```powershell
python -m app.market_reader.engine_trend.db_cli_preview `
  --symbol ETHUSDT `
  --interval 15m `
  --max-candles 96 `
  --output reports\engine_trend\db_cli_preview\ethusdt_15m_result.json `
  --preview-output reports\engine_trend\db_cli_preview\ethusdt_15m_preview.json
```

## SOLUSDT 15m

```powershell
python -m app.market_reader.engine_trend.db_cli_preview `
  --symbol SOLUSDT `
  --interval 15m `
  --max-candles 96 `
  --output reports\engine_trend\db_cli_preview\solusdt_15m_result.json `
  --preview-output reports\engine_trend\db_cli_preview\solusdt_15m_preview.json
```

After regenerating evidence, update artifact SHA256 values in the manifest and run the offline acceptance test plus the relevant ENGINE-TREND suite.
