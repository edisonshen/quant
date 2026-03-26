# Migration Plan: stock_id → symbol

Replace `stock_id` (integer FK to `stocks.id`) with `symbol` (string FK to `stocks.symbol`) across all tables.

## Why

- `stock_id` is a meaningless integer — every query needs a join to get the ticker
- `symbol` (e.g. "NVDA", "AAPL") is the natural key used everywhere in the code
- Simpler queries, more readable data, fewer joins

## Affected Tables

| Table | Current FK | New FK | Notes |
|---|---|---|---|
| `money_flow_snapshots` | `stock_id → stocks.id` | `symbol → stocks.symbol` | Largest table (~40k rows) |
| `stock_capital_flow` | `stock_id → stocks.id` | `symbol → stocks.symbol` | |
| `capital_flow_bars` | `stock_id → stocks.id` | `symbol → stocks.symbol` | |
| `stock_prices` | `stock_id → stocks.id` | `symbol → stocks.symbol` | Has unique constraint `(stock_id, date)` → `(symbol, date)` |
| `chart_images` | `stock_id → stocks.id` | `symbol → stocks.symbol` | |

## Affected Code

| File | Changes |
|---|---|
| `core/models.py` | Replace `stock_id` columns with `symbol` FK, add index |
| `core/types.py` | Remove `stock_id` from `MoneyFlowSignal` |
| `scrapers/qu/scraper.py` | Use `symbol` directly, no get-or-create Stock lookup for FK |
| `analysis/stock_screener.py` | Remove `.join(Stock)` for symbol, use `symbol` directly |
| `analysis/sector_analyzer.py` | Remove `.join(Stock)` |
| `backtest/qu100_backtest.py` | Remove `.join(Stock)` |

## Migration Steps

### Step 1: Add `symbol` column to all tables (non-breaking)

```sql
ALTER TABLE money_flow_snapshots ADD COLUMN symbol VARCHAR(10);
ALTER TABLE stock_capital_flow ADD COLUMN symbol VARCHAR(10);
ALTER TABLE capital_flow_bars ADD COLUMN symbol VARCHAR(10);
ALTER TABLE stock_prices ADD COLUMN symbol VARCHAR(10);
ALTER TABLE chart_images ADD COLUMN symbol VARCHAR(10);
```

### Step 2: Backfill `symbol` from `stocks` table

```sql
UPDATE money_flow_snapshots m SET symbol = s.symbol FROM stocks s WHERE m.stock_id = s.id;
UPDATE stock_capital_flow c SET symbol = s.symbol FROM stocks s WHERE c.stock_id = s.id;
UPDATE capital_flow_bars c SET symbol = s.symbol FROM stocks s WHERE c.stock_id = s.id;
UPDATE stock_prices p SET symbol = s.symbol FROM stocks s WHERE p.stock_id = s.id;
UPDATE chart_images c SET symbol = s.symbol FROM stocks s WHERE c.stock_id = s.id;
```

### Step 3: Make `symbol` NOT NULL + add index

```sql
ALTER TABLE money_flow_snapshots ALTER COLUMN symbol SET NOT NULL;
ALTER TABLE stock_capital_flow ALTER COLUMN symbol SET NOT NULL;
ALTER TABLE capital_flow_bars ALTER COLUMN symbol SET NOT NULL;
ALTER TABLE stock_prices ALTER COLUMN symbol SET NOT NULL;
ALTER TABLE chart_images ALTER COLUMN symbol SET NOT NULL;

CREATE INDEX ix_mfs_symbol ON money_flow_snapshots (symbol);
CREATE INDEX ix_scf_symbol ON stock_capital_flow (symbol);
CREATE INDEX ix_cfb_symbol ON capital_flow_bars (symbol);
CREATE INDEX ix_sp_symbol ON stock_prices (symbol);
CREATE INDEX ix_ci_symbol ON chart_images (symbol);
```

### Step 4: Add FK constraint to `stocks.symbol`

```sql
ALTER TABLE money_flow_snapshots ADD CONSTRAINT fk_mfs_symbol FOREIGN KEY (symbol) REFERENCES stocks(symbol);
ALTER TABLE stock_capital_flow ADD CONSTRAINT fk_scf_symbol FOREIGN KEY (symbol) REFERENCES stocks(symbol);
ALTER TABLE capital_flow_bars ADD CONSTRAINT fk_cfb_symbol FOREIGN KEY (symbol) REFERENCES stocks(symbol);
ALTER TABLE stock_prices ADD CONSTRAINT fk_sp_symbol FOREIGN KEY (symbol) REFERENCES stocks(symbol);
ALTER TABLE chart_images ADD CONSTRAINT fk_ci_symbol FOREIGN KEY (symbol) REFERENCES stocks(symbol);
```

### Step 5: Update models + code

- Update `core/models.py` — replace `stock_id` with `symbol` FK
- Update `core/types.py` — remove `stock_id` from `MoneyFlowSignal`
- Update `scrapers/qu/scraper.py` — use symbol directly
- Update `analysis/stock_screener.py` — remove Stock joins
- Update `analysis/sector_analyzer.py` — remove Stock joins
- Update `backtest/qu100_backtest.py` — remove Stock joins

### Step 6: Drop old `stock_id` columns + FK constraints

```sql
ALTER TABLE money_flow_snapshots DROP CONSTRAINT money_flow_snapshots_stock_id_fkey;
ALTER TABLE stock_capital_flow DROP CONSTRAINT stock_capital_flow_stock_id_fkey;
ALTER TABLE capital_flow_bars DROP CONSTRAINT capital_flow_bars_stock_id_fkey;
ALTER TABLE stock_prices DROP CONSTRAINT stock_prices_stock_id_fkey;
ALTER TABLE chart_images DROP CONSTRAINT chart_images_stock_id_fkey;

ALTER TABLE money_flow_snapshots DROP COLUMN stock_id;
ALTER TABLE stock_capital_flow DROP COLUMN stock_id;
ALTER TABLE capital_flow_bars DROP COLUMN stock_id;
ALTER TABLE stock_prices DROP COLUMN stock_id;
ALTER TABLE chart_images DROP COLUMN stock_id;
```

### Step 7: Update StockPrice unique constraint

```sql
ALTER TABLE stock_prices DROP CONSTRAINT uq_stock_price_date;
ALTER TABLE stock_prices ADD CONSTRAINT uq_stock_price_date UNIQUE (symbol, date);
```

## Rollback

If anything goes wrong, `stock_id` columns are still present until Step 6. Roll back by reverting the code changes only.

## Validation

After migration:
```sql
-- Verify no NULLs
SELECT COUNT(*) FROM money_flow_snapshots WHERE symbol IS NULL;
-- Verify FK integrity
SELECT m.symbol FROM money_flow_snapshots m LEFT JOIN stocks s ON m.symbol = s.symbol WHERE s.symbol IS NULL;
-- Verify row counts match
SELECT COUNT(*) FROM money_flow_snapshots;
```
