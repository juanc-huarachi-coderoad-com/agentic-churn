-- specs/030-real-warehouse-connector/quickstart.md — EXAMPLE query, replace with
-- a real query against your own warehouse's actual schema before real use.
--
-- WarehouseCollector requires exactly these four columns (any extras are
-- ignored): occurred_at, metric, product_area (nullable), value_delta_pct.
-- This connector never computes the delta itself (REQ-M1-P1/P2) — your query
-- is responsible for that, and for scoping itself to relevant, recent data
-- (research.md Decision 5): this connector does not derive a time window.
--
-- This placeholder returns zero rows against this application's own database
-- (no such table exists here) — it exists only so a fresh checkout has
-- something at the default WAREHOUSE_QUERY_PATH to point at locally, not as
-- a real, runnable example against any actual warehouse.
SELECT
    measured_at AS occurred_at,
    metric_name AS metric,
    product_area,
    delta_pct AS value_delta_pct
FROM product_usage_weekly
WHERE measured_at >= now() - interval '7 days';
