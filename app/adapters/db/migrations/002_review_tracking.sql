-- Vigie — migration 002 — 2026-11-03
-- Ajoute review_reason à recommendations (le motif de décision n'était pas persisté)

ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS review_reason TEXT;
