PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS players (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  birth_date TEXT,
  nationality TEXT,
  height_cm INTEGER,
  weight_kg INTEGER,
  dominant_foot TEXT,
  is_retired INTEGER DEFAULT 0,
  over_35 INTEGER DEFAULT 0,
  retired_since TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teams (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  country TEXT,
  logo_url TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_seasons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id TEXT NOT NULL,
  season INTEGER NOT NULL,
  team_id TEXT,
  league_id TEXT,
  appearances INTEGER,
  goals INTEGER,
  assists INTEGER,
  minutes INTEGER,
  position TEXT,
  rating REAL,
  xg REAL,
  xa REAL,
  key_passes INTEGER,
  successful_dribbles INTEGER,
  duels_won INTEGER,
  shots_per_game REAL,
  tackles_per_game REAL,
  fouls_drawn INTEGER,
  sprint_speed_kmh REAL,
  acceleration TEXT,
  stamina TEXT,
  recovery_rate TEXT,
  contribution_to_build_up TEXT,
  defensive_transitions TEXT,
  raw_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (player_id, season, team_id, league_id),
  FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
  FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS season_national_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_season_id INTEGER NOT NULL,
  team_id TEXT,
  competition TEXT,
  appearances INTEGER,
  goals INTEGER,
  assists INTEGER,
  minutes INTEGER,
  position TEXT,
  rating REAL,
  raw_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (player_season_id) REFERENCES player_seasons(id) ON DELETE CASCADE,
  FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS injuries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_season_id INTEGER NOT NULL,
  injury_type TEXT,
  start_date TEXT,
  end_date TEXT,
  days_lost INTEGER,
  source TEXT,
  raw_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (player_season_id) REFERENCES player_seasons(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transfers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_season_id INTEGER NOT NULL,
  from_team_id TEXT,
  to_team_id TEXT,
  transfer_fee TEXT,
  transfer_date TEXT,
  source TEXT,
  raw_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (player_season_id) REFERENCES player_seasons(id) ON DELETE CASCADE,
  FOREIGN KEY (from_team_id) REFERENCES teams(id),
  FOREIGN KEY (to_team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS prediction_runs (
  id TEXT PRIMARY KEY,
  run_type TEXT NOT NULL DEFAULT 'scheduled',
  status TEXT NOT NULL,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TEXT,
  model_version TEXT,
  triggered_by TEXT,
  error_message TEXT,
  meta TEXT
);

CREATE TABLE IF NOT EXISTS player_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  predicted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  horizon_seasons INTEGER NOT NULL DEFAULT 1,
  prediction_json TEXT NOT NULL,
  confidence_score REAL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (run_id, player_id, horizon_seasons),
  FOREIGN KEY (run_id) REFERENCES prediction_runs(id) ON DELETE CASCADE,
  FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_player_seasons_player_season
  ON player_seasons(player_id, season);

CREATE INDEX IF NOT EXISTS idx_predictions_player
  ON player_predictions(player_id, predicted_at DESC);

CREATE INDEX IF NOT EXISTS idx_runs_status_started
  ON prediction_runs(status, started_at DESC);

DROP VIEW IF EXISTS latest_player_predictions;
CREATE VIEW latest_player_predictions AS
SELECT
  ranked.player_id,
  ranked.run_id,
  ranked.predicted_at,
  ranked.horizon_seasons,
  ranked.prediction_json,
  ranked.confidence_score
FROM (
  SELECT
    pp.player_id,
    pp.run_id,
    pp.predicted_at,
    pp.horizon_seasons,
    pp.prediction_json,
    pp.confidence_score,
    ROW_NUMBER() OVER (
      PARTITION BY pp.player_id
      ORDER BY pp.predicted_at DESC, pp.id DESC
    ) AS rn
  FROM player_predictions pp
  JOIN prediction_runs pr ON pr.id = pp.run_id
  WHERE pr.status = 'success'
) ranked
WHERE ranked.rn = 1;
