-- ============================================================
-- Wara demo — backdated score history (30-day depth)
-- ============================================================
-- Inserts 30 score_runs rows (Jul 18 - Aug 16, 2026) with matching
-- band_history rows, telling the visual story of a healthy account
-- gently trending up, then sliding into Watch as small, easy-to-read
-- problems (inventory sync hiccups, a quieter CTO and dev lead) pile up.
--
-- Stage 1 target: the REAL score computed on Aug 17 by compute_score.py
-- from the actual findings in `wara-concerning.json` lands at
-- approximately 55-61 (Watch, upper end) — see INSTALL.md's worked
-- arithmetic table for the exact per-finding math behind that number.
-- This backfill's job is only to set up believable history and correct
-- hysteresis state BEFORE that real computation, not to guess the final
-- number itself.
--
-- The 31st point (Aug 17, today) comes from the real
-- compute_score.py runs — NOT from this script.
--
-- NOTE — dashboard visibility: the live dashboard's trend query
-- (`_TREND_DAYS = 14` in `backend/app/experience/application/use_cases.py`,
-- intentionally unmodified) only ever renders the most recent 14 days.
-- So only Aug 4-17 will appear on the sparkline; the Jul 18 - Aug 3
-- prelude exists in `score_runs` for anyone querying it directly (or for
-- a future deeper trend view) but is not visible in today's UI. This is
-- expected, not a bug in the backfill.
--
-- Run AFTER the Wara profile has been loaded (POST /api/profile/reload),
-- AFTER the readers have run (so findings exist), and BEFORE the two
-- compute_score.py runs.
--
-- This script first wipes any score_runs/band_history created by the
-- profile-reload's automatic score recompute (which had no findings and
-- produced score=0, band=healthy). That cleanup ensures the real
-- compute_score.py runs read the backdated Watch band_history as the
-- latest prior state, so hysteresis settles correctly on the first run.
--
-- Trend trajectory (gentle rise, then a run of small, related problems):
--   Jul 18-Aug 7:  healthy  (14-28, green/silver, gentle oscillating rise)
--   Aug 8:         healthy->watch transition row (raw_band flips first,
--                  displayed band lags one run — REQ-M6-19)
--   Aug 9-16:      watch    (38-56, amber) — 8 consecutive runs, so the
--                  real Aug 17 computation (also landing in Watch) settles
--                  immediately instead of fighting hysteresis.
--   Aug 17:        real score from compute_score.py (expected ~55-61)
--
-- `consecutive_runs_in_band` counts consecutive runs in the same
-- *displayed* band (not raw_band).
-- ============================================================
-- Step 1 — Clean up any prior score_runs/band_history
-- ============================================================
-- POST /api/profile/reload triggers an automatic score recompute that
-- creates a score_run (score=0, band=healthy) and a band_history row.
-- Delete those so the backfilled Watch history is the latest prior
-- state for the real compute_score.py runs.
-- (Safe to run as the postgres superuser via docker compose exec db psql.)
-- ============================================================

DELETE FROM narrator_outputs;
DELETE FROM score_contributions;
DELETE FROM band_history;
DELETE FROM score_runs;

-- ============================================================
-- Step 2 — Insert 30 backdated score_runs + band_history rows
-- ============================================================

WITH profile AS (
    SELECT id AS pv_id
    FROM client_profile_versions
    WHERE is_current
    LIMIT 1
),
data AS (
    SELECT * FROM (VALUES
        ('2026-07-18T12:00:00-05:00'::timestamptz, 14.00::numeric(5,2), 'healthy'::band, 'healthy'::band, 1),
        ('2026-07-19T12:00:00-05:00'::timestamptz, 15.00, 'healthy', 'healthy', 2),
        ('2026-07-20T12:00:00-05:00'::timestamptz, 14.00, 'healthy', 'healthy', 3),
        ('2026-07-21T12:00:00-05:00'::timestamptz, 16.00, 'healthy', 'healthy', 4),
        ('2026-07-22T12:00:00-05:00'::timestamptz, 15.00, 'healthy', 'healthy', 5),
        ('2026-07-23T12:00:00-05:00'::timestamptz, 17.00, 'healthy', 'healthy', 6),
        ('2026-07-24T12:00:00-05:00'::timestamptz, 16.00, 'healthy', 'healthy', 7),
        ('2026-07-25T12:00:00-05:00'::timestamptz, 18.00, 'healthy', 'healthy', 8),
        ('2026-07-26T12:00:00-05:00'::timestamptz, 17.00, 'healthy', 'healthy', 9),
        ('2026-07-27T12:00:00-05:00'::timestamptz, 19.00, 'healthy', 'healthy', 10),
        ('2026-07-28T12:00:00-05:00'::timestamptz, 18.00, 'healthy', 'healthy', 11),
        ('2026-07-29T12:00:00-05:00'::timestamptz, 20.00, 'healthy', 'healthy', 12),
        ('2026-07-30T12:00:00-05:00'::timestamptz, 19.00, 'healthy', 'healthy', 13),
        ('2026-07-31T12:00:00-05:00'::timestamptz, 21.00, 'healthy', 'healthy', 14),
        ('2026-08-01T12:00:00-05:00'::timestamptz, 20.00, 'healthy', 'healthy', 15),
        ('2026-08-02T12:00:00-05:00'::timestamptz, 21.00, 'healthy', 'healthy', 16),
        ('2026-08-03T12:00:00-05:00'::timestamptz, 21.00, 'healthy', 'healthy', 17),
        ('2026-08-04T12:00:00-05:00'::timestamptz, 22.00, 'healthy', 'healthy', 18),
        ('2026-08-05T12:00:00-05:00'::timestamptz, 24.00, 'healthy', 'healthy', 19),
        ('2026-08-06T12:00:00-05:00'::timestamptz, 26.00, 'healthy', 'healthy', 20),
        ('2026-08-07T12:00:00-05:00'::timestamptz, 28.00, 'healthy', 'healthy', 21),
        ('2026-08-08T12:00:00-05:00'::timestamptz, 33.00, 'healthy', 'watch',      22),
        ('2026-08-09T12:00:00-05:00'::timestamptz, 38.00, 'watch',   'watch',      1),
        ('2026-08-10T12:00:00-05:00'::timestamptz, 41.00, 'watch',   'watch',      2),
        ('2026-08-11T12:00:00-05:00'::timestamptz, 44.00, 'watch',   'watch',      3),
        ('2026-08-12T12:00:00-05:00'::timestamptz, 47.00, 'watch',   'watch',      4),
        ('2026-08-13T12:00:00-05:00'::timestamptz, 50.00, 'watch',   'watch',      5),
        ('2026-08-14T12:00:00-05:00'::timestamptz, 52.00, 'watch',   'watch',      6),
        ('2026-08-15T12:00:00-05:00'::timestamptz, 54.00, 'watch',   'watch',      7),
        ('2026-08-16T12:00:00-05:00'::timestamptz, 56.00, 'watch',   'watch',      8)
    ) AS t(computed_at, score, band, raw_band, consecutive)
),
runs AS (
    INSERT INTO score_runs (
        trigger,
        profile_version_id,
        finding_type_config_version,
        total_negative_points,
        total_positive_points,
        positive_points_applied,
        total_points,
        score,
        band,
        raw_band,
        source_degraded,
        is_frozen,
        computed_at
    )
    SELECT
        'manual'::score_trigger,
        p.pv_id,
        'v1',
        d.score,
        0,
        0,
        d.score,
        d.score,
        d.band,
        d.raw_band,
        false,
        false,
        d.computed_at
    FROM data d, profile p
    RETURNING id, computed_at
)
INSERT INTO band_history (score_run_id, band, consecutive_runs_in_band, created_at)
SELECT
    r.id,
    d.band,
    d.consecutive,
    r.computed_at
FROM runs r
JOIN data d ON r.computed_at = d.computed_at;

-- ============================================================
-- Verification (optional — run to confirm the backfill landed)
-- ============================================================
-- SELECT
--     computed_at,
--     score,
--     band,
--     raw_band
-- FROM score_runs
-- ORDER BY computed_at ASC;
--
-- Expected: 30 rows, Jul 18 (score 14, healthy) through Aug 16 (score 56, watch).
