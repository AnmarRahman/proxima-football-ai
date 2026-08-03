create table if not exists ml_players (
  id text primary key,
  name text not null,
  birth_date date not null,
  nationality text,
  primary_position text,
  position_group text,
  coarse_group text not null check (coarse_group in ('DEF', 'MID', 'WIDE', 'FWD', 'GK')),
  career_status text not null check (career_status in ('active', 'retired', 'inactive', 'unknown')),
  stat_scope text not null default 'domestic_league' check (stat_scope = 'domestic_league'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ml_player_seasons (
  id bigserial primary key,
  player_id text not null references ml_players(id) on delete cascade,
  canonical_season text not null,
  season_start_year int not null,
  season_end_year int not null,
  season_format text not null check (season_format in ('split_year', 'calendar_year')),
  appearances int not null check (appearances >= 0),
  goals int not null check (goals >= 0),
  is_partial boolean not null default false,
  model_eligible boolean not null default true,
  source_row jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (player_id, canonical_season)
);

create table if not exists model_versions (
  version text primary key,
  data_version text not null,
  manifest_sha256 text not null,
  training_csv_sha256 text not null,
  source_git_commit text,
  trained_at timestamptz,
  approved boolean not null default false,
  metrics jsonb not null default '{}'::jsonb,
  manifest jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists tier_a_prediction_runs (
  id uuid primary key default gen_random_uuid(),
  status text not null check (status in ('running', 'success', 'failed')),
  run_type text not null default 'manual',
  triggered_by text,
  model_version text references model_versions(version),
  requested_player_id text,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  predicted_count int not null default 0,
  rejected_count int not null default 0,
  error_message text,
  meta jsonb not null default '{}'::jsonb
);

create table if not exists next_season_predictions (
  player_id text primary key references ml_players(id) on delete cascade,
  run_id uuid not null references tier_a_prediction_runs(id) on delete cascade,
  model_version text not null references model_versions(version),
  prediction_scope text not null check (prediction_scope = 'next_domestic_league_season'),
  prediction_point text not null check (prediction_point in ('next', 'latest-completed')),
  based_on_season text,
  predicted_season text,
  appearances_expected int not null check (appearances_expected >= 0),
  appearances_lower int check (appearances_lower >= 0),
  appearances_upper int check (appearances_upper >= 0),
  appearances_interval_method text,
  appearances_interval_unavailable_reason text,
  goals_expected int not null check (goals_expected >= 0),
  goals_lower int check (goals_lower >= 0),
  goals_upper int check (goals_upper >= 0),
  goals_interval_method text,
  limitations jsonb not null default '[]'::jsonb,
  coverage_metadata jsonb not null default '{}'::jsonb,
  prediction_json jsonb not null,
  input_sha256 text not null,
  predicted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (appearances_lower is null or appearances_upper is null or appearances_lower <= appearances_upper),
  check (goals_lower is null or goals_upper is null or goals_lower <= goals_upper)
);

create index if not exists idx_ml_seasons_player_year
  on ml_player_seasons(player_id, season_start_year);
create index if not exists idx_tier_a_runs_started
  on tier_a_prediction_runs(started_at desc);
create index if not exists idx_next_predictions_time
  on next_season_predictions(predicted_at desc);

alter table ml_players enable row level security;
alter table ml_player_seasons enable row level security;
alter table model_versions enable row level security;
alter table tier_a_prediction_runs enable row level security;
alter table next_season_predictions enable row level security;

-- Supabase server routes use service_role. Keep the migration portable to
-- ordinary Postgres installations where that role does not exist.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant usage on schema public to service_role;
    grant select, insert, update, delete on
      ml_players, ml_player_seasons, model_versions,
      tier_a_prediction_runs, next_season_predictions
      to service_role;
    grant usage, select on all sequences in schema public to service_role;
  end if;
end
$$;

create or replace view latest_tier_a_prediction_runs as
select *
from tier_a_prediction_runs
order by started_at desc
limit 20;
