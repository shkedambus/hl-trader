CREATE TABLE IF NOT EXISTS methodology_versions (
    version      TEXT PRIMARY KEY,
    parameters   JSONB NOT NULL,
    effective_at TIMESTAMPTZ NOT NULL
);

-- Leaderboard accounts that passed the prefilter (FR-1).
CREATE TABLE IF NOT EXISTS candidates (
    address         TEXT PRIMARY KEY,
    first_seen      TIMESTAMPTZ NOT NULL,
    last_refreshed  TIMESTAMPTZ NOT NULL,
    account_value   NUMERIC NOT NULL,
    pnl_all_time    NUMERIC NOT NULL,
    roi_all_time    DOUBLE PRECISION NOT NULL,
    volume_all_time NUMERIC NOT NULL,
    priority        DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_candidates_queue ON candidates (priority DESC);

-- FR-2. NULL means "no data", which is not the same as zero.
CREATE TABLE IF NOT EXISTS trader_metrics (
    id               BIGSERIAL PRIMARY KEY,
    address          TEXT NOT NULL,
    computed_at      TIMESTAMPTZ NOT NULL,
    window_days      DOUBLE PRECISION NOT NULL,
    tenure_days      DOUBLE PRECISION NOT NULL,
    account_value    NUMERIC NOT NULL,
    sharpe           DOUBLE PRECISION,
    max_drawdown     DOUBLE PRECISION,
    portfolio_points INTEGER NOT NULL,
    round_trips      INTEGER NOT NULL,
    win_rate         DOUBLE PRECISION,
    profit_factor    DOUBLE PRECISION,
    expectancy_pct   DOUBLE PRECISION,
    median_hold_s    DOUBLE PRECISION,
    fills_count      INTEGER NOT NULL,
    fills_per_day    DOUBLE PRECISION NOT NULL,
    fills_truncated  BOOLEAN NOT NULL,
    liquidated_share DOUBLE PRECISION,
    coins            TEXT[] NOT NULL,
    UNIQUE (address, computed_at)
);
CREATE INDEX IF NOT EXISTS idx_trader_metrics_latest ON trader_metrics (address, computed_at DESC);

-- FR-3...FR-7. A rescore (FR-8) adds rows under a new version and never touches old ones.
CREATE TABLE IF NOT EXISTS verdicts (
    id                  BIGSERIAL PRIMARY KEY,
    address             TEXT NOT NULL,
    metrics_id          BIGINT NOT NULL REFERENCES trader_metrics (id),
    methodology_version TEXT NOT NULL REFERENCES methodology_versions (version),
    judged_at           TIMESTAMPTZ NOT NULL,
    selected            BOOLEAN NOT NULL,
    is_tracked          BOOLEAN NOT NULL DEFAULT FALSE,
    score               DOUBLE PRECISION NOT NULL,
    confidence          DOUBLE PRECISION NOT NULL,
    style               TEXT NOT NULL,
    contributions       JSONB NOT NULL,
    checks              JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_verdicts_latest ON verdicts (address, judged_at DESC);
CREATE INDEX IF NOT EXISTS idx_verdicts_ranking ON verdicts (judged_at, score DESC) WHERE selected;

-- Last observed positions of tracked traders: the baseline the next poll compares to (FR-9).
CREATE TABLE IF NOT EXISTS positions (
    address     TEXT NOT NULL,
    coin        TEXT NOT NULL,
    direction   TEXT NOT NULL,
    size        NUMERIC NOT NULL,
    notional    NUMERIC NOT NULL,
    leverage    NUMERIC,
    entry_px    NUMERIC,
    observed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (address, coin)
);

-- Position changes (FR-9) and reviews of the verdict (FR-10). `id` is the delivery cursor.
CREATE TABLE IF NOT EXISTS events (
    id          BIGSERIAL PRIMARY KEY,
    address     TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('position', 'review')),
    event_type  TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload     JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_address ON events (address, occurred_at);

CREATE TABLE IF NOT EXISTS subscriptions (
    chat_id    BIGINT NOT NULL,
    address    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (chat_id, address)
);

CREATE TABLE IF NOT EXISTS deliveries (
    event_id     BIGINT NOT NULL REFERENCES events (id),
    chat_id      BIGINT NOT NULL,
    delivered_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (event_id, chat_id)
);
