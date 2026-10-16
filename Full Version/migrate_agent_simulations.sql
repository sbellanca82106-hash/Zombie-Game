-- Run this once against your existing zombie_game database.
-- It preserves existing rows; older rows receive power=1 and simulation_id=NULL.

CREATE TABLE IF NOT EXISTS simulations (
    simulation_id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    starting_humans INTEGER NOT NULL CHECK (starting_humans >= 0),
    starting_zombies INTEGER NOT NULL CHECK (starting_zombies >= 0)
);

ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS simulation_id BIGINT
    REFERENCES simulations(simulation_id) ON DELETE CASCADE;

ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS power INTEGER NOT NULL DEFAULT 1
    CHECK (power >= 0);

CREATE INDEX IF NOT EXISTS idx_agents_simulation_id
    ON agents(simulation_id);
