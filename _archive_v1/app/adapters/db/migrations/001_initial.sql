-- Vigie — schéma initial PostgreSQL
-- Migration 001 — 2026-11-04

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- alerts : événements bruts SIEM
CREATE TABLE IF NOT EXISTS alerts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT,
    severity    TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    source      TEXT NOT NULL,
    title       TEXT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}',
    incident_id UUID,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- incidents : groupes corrélés d'alertes
CREATE TABLE IF NOT EXISTS incidents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status           TEXT NOT NULL DEFAULT 'open'
                         CHECK (status IN ('open','in_progress','resolved','closed')),
    severity         TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    title            TEXT NOT NULL,
    mitre_techniques TEXT[] NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- FK alerts → incidents (posée après les deux tables)
ALTER TABLE alerts
    ADD CONSTRAINT fk_alerts_incident
    FOREIGN KEY (incident_id) REFERENCES incidents(id);

-- agent_runs : suivi des exécutions LangGraph
CREATE TABLE IF NOT EXISTS agent_runs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id   UUID NOT NULL REFERENCES incidents(id),
    run_type      TEXT NOT NULL CHECK (run_type IN ('triage','enrichissement','recommandation')),
    llm_model     TEXT NOT NULL,
    tokens_in     INT,
    tokens_out    INT,
    latency_ms    INT,
    status        TEXT NOT NULL CHECK (status IN ('running','success','error')),
    error_message TEXT,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMPTZ
);

-- recommendations : sorties de l'agent par incident
CREATE TABLE IF NOT EXISTS recommendations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id  UUID NOT NULL REFERENCES incidents(id),
    agent_run_id UUID NOT NULL REFERENCES agent_runs(id),
    content      TEXT NOT NULL,
    confidence   FLOAT,
    mitre_refs   TEXT[] NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','approved','rejected','applied')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at  TIMESTAMPTZ,
    reviewed_by  TEXT
);

-- audit_log : actions humaines (AI Act article 14)
CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('recommendation','incident')),
    entity_id   UUID NOT NULL,
    action      TEXT NOT NULL CHECK (action IN ('approved','rejected','escalated','applied')),
    actor       TEXT NOT NULL,
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index utiles
CREATE INDEX IF NOT EXISTS idx_alerts_incident ON alerts(incident_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_incident ON agent_runs(incident_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_incident ON recommendations(incident_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_id);
