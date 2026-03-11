create extension if not exists pgcrypto;

create table if not exists players (
  id text primary key,
  name text not null,
  birth_date date,
  nationality text,
  height_cm int,
  weight_kg int,
  dominant_foot text,
  is_retired boolean default false,
  retired_since date,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists teams (
  id text primary key,
  name text not null,
  country text,
  logo_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists player_seasons (
  id bigserial primary key,
  player_id text not null references players(id) on delete cascade,
  season int not null,
  team_id text references teams(id),
  league_id text,
  appearances int,
  goals int,
  assists int,
  minutes int,
  position text,
  rating numeric(4,2),
  xg numeric(8,3),
  xa numeric(8,3),
  key_passes int,
  successful_dribbles int,
  duels_won int,
  shots_per_game numeric(6,3),
  tackles_per_game numeric(6,3),
  fouls_drawn int,
  sprint_speed_kmh numeric(6,3),
  acceleration text,
  stamina text,
  recovery_rate text,
  contribution_to_build_up text,
  defensive_transitions text,
  raw_json jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (player_id, season, team_id, league_id)
);

create table if not exists season_national_stats (
  id bigserial primary key,
  player_season_id bigint not null references player_seasons(id) on delete cascade,
  team_id text references teams(id),
  competition text,
  appearances int,
  goals int,
  assists int,
  minutes int,
  position text,
  rating numeric(4,2),
  raw_json jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists injuries (
  id bigserial primary key,
  player_season_id bigint not null references player_seasons(id) on delete cascade,
  injury_type text,
  start_date date,
  end_date date,
  days_lost int,
  source text,
  raw_json jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists transfers (
  id bigserial primary key,
  player_season_id bigint not null references player_seasons(id) on delete cascade,
  from_team_id text references teams(id),
  to_team_id text references teams(id),
  transfer_fee text,
  transfer_date date,
  source text,
  raw_json jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists prediction_runs (
  id uuid primary key default gen_random_uuid(),
  run_type text not null default 'scheduled',
  status text not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  model_version text,
  triggered_by text,
  error_message text,
  meta jsonb
);

create table if not exists player_predictions (
  id bigserial primary key,
  run_id uuid not null references prediction_runs(id) on delete cascade,
  player_id text not null references players(id) on delete cascade,
  predicted_at timestamptz not null default now(),
  horizon_seasons int not null default 1,
  prediction_json jsonb not null,
  confidence_score numeric(6,3),
  created_at timestamptz default now(),
  unique (run_id, player_id, horizon_seasons)
);

create index if not exists idx_player_seasons_player_season on player_seasons(player_id, season);
create index if not exists idx_predictions_player on player_predictions(player_id, predicted_at desc);
create index if not exists idx_runs_status_started on prediction_runs(status, started_at desc);

create or replace view latest_player_predictions as
select distinct on (pp.player_id)
  pp.player_id,
  pp.run_id,
  pp.predicted_at,
  pp.horizon_seasons,
  pp.prediction_json,
  pp.confidence_score
from player_predictions pp
join prediction_runs pr on pr.id = pp.run_id
where pr.status = 'success'
order by pp.player_id, pp.predicted_at desc;
