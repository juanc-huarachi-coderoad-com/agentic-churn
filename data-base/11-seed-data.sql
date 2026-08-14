-- ============================================================
-- 11 · Seed data
-- Runnable PostgreSQL seed data for a local/demo deployment.
-- Matches the Meridian Logistics scenario used throughout this
-- documentation set (examples/01-end-to-end-walkthrough.md,
-- requirements/13-scoring-calibration-appendix.md,
-- data-base/05-schema-reasoning.md, data-base/07-schema-feedback.md).
--
-- Run this AFTER data-base/10-ddl-appendix.md's DDL. Uses fixed,
-- readable UUIDs (not gen_random_uuid()) so fixtures, tests, and this
-- documentation set can all refer to the same rows by name.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- Users (requirements/14-authentication.md, data-base/12)
-- marta's hash is a real Argon2id hash of the local/demo-only password
-- "agentic-demo-2026" (specs/002-dashboard-shell/research.md §Decision:
-- Regenerating the seeded demo password hash) — never treated as a secret,
-- but still real enough to actually exercise the login flow. support's
-- password is a placeholder still, since no feature yet needs to log in as
-- that user — replace before any real deployment either way.
-- ------------------------------------------------------------
INSERT INTO users (id, username, password_hash, display_name, role, is_active) VALUES
    ('00000000-0000-0000-0000-000000000001', 'marta',   '$argon2id$v=19$m=65536,t=3,p=4$F5VLyj2y64Fc1s7L96wYhQ$w78e3NIpjyF+HIRpXjSrFY8CgrENRySWW4JzLwNZ1AM', 'Marta',   'cs_lead', true),
    ('00000000-0000-0000-0000-000000000002', 'support', '$argon2id$v=19$m=65536,t=3,p=4$REPLACE_ME_DEMO_ONLY', 'Support Lead', 'support_lead', true);

-- ------------------------------------------------------------
-- Sources (data-base/02-schema-ingestion.md)
-- MVP sources (gmail, zendesk, warehouse) plus the two Post-MVP
-- sources used in the full-capability worked example (slack, csat) —
-- see decisions/01-mvp-scope-and-phasing.md for which are actually
-- wired up in a Phase 1 deployment.
-- ------------------------------------------------------------
INSERT INTO sources (id, source_type, display_name, auth_scope, status) VALUES
    ('10000000-0000-0000-0000-000000000001', 'gmail',     'Meridian — Email',          'gmail.readonly',        'connected'),
    ('10000000-0000-0000-0000-000000000002', 'zendesk',   'Meridian — Support',        'zendesk.tickets.read',  'connected'),
    ('10000000-0000-0000-0000-000000000003', 'warehouse', 'Meridian — Product usage',  'warehouse.readonly',    'connected'),
    ('10000000-0000-0000-0000-000000000004', 'slack',     'Meridian — Slack Connect',  'slack.channels.read',   'connected'),
    ('10000000-0000-0000-0000-000000000005', 'csat',      'Meridian — CSAT',           'csat.readonly',         'connected');

-- ------------------------------------------------------------
-- Client profile (data-base/04-schema-context.md)
-- ------------------------------------------------------------
INSERT INTO client_profile_versions
    (id, version_number, client_name, renewal_date, contract_value_band, business_goals,
     working_hours_start, working_hours_end, timezone, languages, communication_norms,
     exclusions, authored_by_user_id, is_current)
VALUES
    ('20000000-0000-0000-0000-000000000001', 3, 'Meridian Logistics', '2026-11-08', 'strategic',
     ARRAY['reduce delivery disputes by 30% this year'],
     '08:00', '18:00', 'America/Bogota', ARRAY['es','en'],
     'Direct communicators. Brevity is habitual, not hostile. Formality rises when senior people are present.',
     ARRAY['legal_threads','commercial_negotiation'],
     '00000000-0000-0000-0000-000000000001', true);

INSERT INTO stakeholders (id, profile_version_id, external_id, name, role, influence, influence_multiplier, signs_renewal, identifiers) VALUES
    ('21000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'stk_ana',   'Ana Reyes',   'CTO',      'sponsor',    1.60, true,  ARRAY['ana.reyes@meridian.com']),
    ('21000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 'stk_diego', 'Diego Marín', 'Dev lead', 'daily_user', 1.20, false, ARRAY['diego@meridian.com']);

INSERT INTO product_areas (id, profile_version_id, key, criticality, criticality_multiplier) VALUES
    ('22000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'tracking_api', 'critical', 1.50),
    ('22000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 'reporting',     'standard', 1.00);

INSERT INTO commitments (id, profile_version_id, type, priority, threshold_business_hours, cadence) VALUES
    ('23000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'first_response', 'P1', 4.0, NULL),
    ('23000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 'recurring_sync',  NULL, NULL, 'weekly');

INSERT INTO profile_history_entries (profile_version_id, event_date, description) VALUES
    ('20000000-0000-0000-0000-000000000001', '2026-03-02', 'Major outage on tracking_api, improvement plan agreed with Ana');

-- ------------------------------------------------------------
-- Identity map (data-base/02-schema-ingestion.md)
-- Ana and Diego resolve cleanly; the Zendesk reporter deliberately
-- does not, matching REQ-M1-05 and the worked example in examples/01.
-- ------------------------------------------------------------
INSERT INTO identity_map (source_identifier, source_type, stakeholder_id, match_confidence, resolved_by) VALUES
    ('ana.reyes@meridian.com',   'gmail', '21000000-0000-0000-0000-000000000001', NULL, 'exact_match'),
    ('diego@meridian.com',       'slack', '21000000-0000-0000-0000-000000000002', NULL, 'exact_match'),
    ('ana.reyes@meridian.com',   'csat',  '21000000-0000-0000-0000-000000000001', NULL, 'exact_match'),
    ('support-desk@meridian.zendesk.com', 'zendesk', NULL, NULL, 'unresolved');

-- ------------------------------------------------------------
-- Finding type config (data-base/05-schema-reasoning.md)
-- The 9 finding types used throughout examples/01-end-to-end-walkthrough.md
-- and specified in requirements/13-scoring-calibration-appendix.md.
-- ------------------------------------------------------------
INSERT INTO finding_type_config (finding_type, base_points, confidence_floor, min_evidence_count, half_life_days, version) VALUES
    ('broken_response_promise', 20.00, 0.50, 1, 14, 'v1'),
    ('tone_deterioration',      10.00, 0.65, 3, 21, 'v1'),
    ('recurring_issue',         12.00, 0.60, 1, 30, 'v1'),
    ('usage_deviation',         15.00, 0.60, 1, 21, 'v1'),
    ('escalation_language',     14.00, 0.60, 1, 14, 'v1'),
    ('contact_absence',         12.00, 0.60, 1, 30, 'v1'),
    ('relationship_change',      8.00, 0.55, 1, 30, 'v1'),
    ('csat_deviation',          10.00, 0.60, 1, 21, 'v1'),
    ('commitment_met',          10.00, 0.50, 1,  7, 'v1');

-- ------------------------------------------------------------
-- Playbook (data-base/08-schema-experience.md)
-- The Phase 1 playbook: 3-5 actions, signed off by Marta
-- (decisions/00-open-questions-resolved.md Q7).
-- ------------------------------------------------------------
INSERT INTO playbook_actions (template_text, applies_to_finding_type, default_owner_role, default_sla_days, signed_off_by_user_id, is_active) VALUES
    ('Escalate {ticket_ref} with engineering {when}',                       'broken_response_promise', 'Support lead', 1, '00000000-0000-0000-0000-000000000001', true),
    ('Call {stakeholder_name} before {deadline} — don''t email',            'escalation_language',     'CS lead',      2, '00000000-0000-0000-0000-000000000001', true),
    ('Check in with {stakeholder_name} — they''ve gone quiet for {days} days', 'contact_absence',      'CS lead',      3, '00000000-0000-0000-0000-000000000001', true),
    ('Review usage drop on {product_area} with the account team',           'usage_deviation',         'CS lead',      5, '00000000-0000-0000-0000-000000000001', true),
    ('Follow up on the CSAT comment directly with {stakeholder_name}',      'csat_deviation',           'CS lead',      3, '00000000-0000-0000-0000-000000000001', true);

COMMIT;

-- ============================================================
-- What this feeds (per the consistency review that requested it):
--   - SimulatedCollector / demo replay mode (demo/01-live-demo-runbook.md)
--   - Golden-replay tests (tests/strategy.md)
--   - The contingency path if a live API integration fails mid-demo
-- ============================================================
