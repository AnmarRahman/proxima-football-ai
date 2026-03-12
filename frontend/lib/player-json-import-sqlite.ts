import { withSqliteDatabase } from "@/lib/sqlite-db";

type Dict = Record<string, unknown>;

type ImportOptions = {
  overAgeThreshold?: number;
};

export type PlayerImportResult = {
  playerId: string;
  playerName: string;
  seasonsImported: number;
};

function asRecord(value: unknown): Dict {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Dict) : {};
}

function recordArray(value: unknown): Dict[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map(asRecord).filter((entry) => Object.keys(entry).length > 0);
}

function normalizeId(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const clean = String(value).trim().toLowerCase();
  return clean ? clean : null;
}

function titleFromId(id: string): string {
  return id
    .split("-")
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}

function toInt(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return Math.trunc(parsed);
}

function toFloat(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function toDateString(value: unknown): string | null {
  if (!value) {
    return null;
  }
  const raw = String(value).trim();
  if (!raw) {
    return null;
  }
  return /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : null;
}

function parseBool(value: unknown, defaultValue: boolean | null = null): boolean | null {
  if (value === null || value === undefined) {
    return defaultValue;
  }
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    return value !== 0;
  }

  const normalized = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "y", "retired"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "n", "active"].includes(normalized)) {
    return false;
  }
  return defaultValue;
}

function parseBirthYear(player: Dict): number | null {
  const birthDate = player.birth_date;
  if (!birthDate) {
    return null;
  }
  const year = Number(String(birthDate).slice(0, 4));
  return Number.isFinite(year) ? year : null;
}

function computeOverAge(player: Dict, seasons: Dict[], threshold: number): boolean {
  const explicit = parseBool(player.over_35 ?? player.over35, null);
  if (explicit !== null) {
    return explicit;
  }

  const birthYear = parseBirthYear(player);
  if (birthYear === null) {
    return false;
  }

  const seasonYears = seasons
    .map((season) => toInt(season.season))
    .filter((year): year is number => year !== null);

  if (!seasonYears.length) {
    return false;
  }

  const lastSeasonYear = Math.max(...seasonYears);
  return lastSeasonYear - birthYear >= threshold;
}

function parseRetired(player: Dict): boolean {
  if ("is_retired" in player || "retired" in player) {
    return Boolean(parseBool(player.is_retired ?? player.retired, false));
  }
  if (player.retired_since) {
    return true;
  }
  return false;
}

function ensureTeam(db: any, teamId: string | null, team: Dict = {}): void {
  if (!teamId) {
    return;
  }

  const nameFromFile = typeof team.name === "string" ? team.name.trim() : "";
  const name = nameFromFile || titleFromId(teamId);
  const country = typeof team.country === "string" && team.country.trim() ? team.country : null;
  const logoUrl = typeof team.logo_url === "string" && team.logo_url.trim() ? team.logo_url : null;

  db.prepare(
    `
    insert into teams(id, name, country, logo_url)
    values (?, ?, ?, ?)
    on conflict(id) do update set
      name = excluded.name,
      country = coalesce(excluded.country, teams.country),
      logo_url = coalesce(excluded.logo_url, teams.logo_url),
      updated_at = CURRENT_TIMESTAMP
    `
  ).run(teamId, name, country, logoUrl);
}

function upsertPlayer(db: any, player: Dict, seasons: Dict[], overAgeThreshold: number): string {
  const playerId = normalizeId(player.id);
  if (!playerId) {
    throw new Error("Missing player.id");
  }

  db.prepare(
    `
    insert into players(
      id, name, birth_date, nationality, height_cm, weight_kg, dominant_foot, is_retired, over_35, retired_since
    )
    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    on conflict(id) do update set
      name = excluded.name,
      birth_date = excluded.birth_date,
      nationality = excluded.nationality,
      height_cm = excluded.height_cm,
      weight_kg = excluded.weight_kg,
      dominant_foot = excluded.dominant_foot,
      is_retired = excluded.is_retired,
      over_35 = excluded.over_35,
      retired_since = excluded.retired_since,
      updated_at = CURRENT_TIMESTAMP
    `
  ).run(
    playerId,
    String(player.name || playerId),
    toDateString(player.birth_date),
    typeof player.nationality === "string" ? player.nationality : null,
    toInt(player.height_cm),
    toInt(player.weight_kg),
    typeof player.dominant_foot === "string" ? player.dominant_foot : null,
    parseRetired(player) ? 1 : 0,
    computeOverAge(player, seasons, overAgeThreshold) ? 1 : 0,
    toDateString(player.retired_since)
  );

  return playerId;
}

function upsertPlayerSeason(db: any, playerId: string, season: Dict): number {
  const seasonYear = toInt(season.season);
  if (seasonYear === null) {
    throw new Error(`Missing or invalid season year for player ${playerId}`);
  }

  const teamId = normalizeId(season.team_id);
  const leagueId = normalizeId(season.league_id) || "unknown";
  const physical = asRecord(season.physical_metrics);
  const tactical = asRecord(season.tactical_data);

  ensureTeam(db, teamId);

  const row = db
    .prepare(
      `
      insert into player_seasons(
        player_id, season, team_id, league_id, appearances, goals, assists, minutes,
        position, rating, xg, xa, key_passes, successful_dribbles, duels_won,
        shots_per_game, tackles_per_game, fouls_drawn,
        sprint_speed_kmh, acceleration, stamina, recovery_rate,
        contribution_to_build_up, defensive_transitions, raw_json
      )
      values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      on conflict(player_id, season, team_id, league_id) do update set
        appearances = excluded.appearances,
        goals = excluded.goals,
        assists = excluded.assists,
        minutes = excluded.minutes,
        position = excluded.position,
        rating = excluded.rating,
        xg = excluded.xg,
        xa = excluded.xa,
        key_passes = excluded.key_passes,
        successful_dribbles = excluded.successful_dribbles,
        duels_won = excluded.duels_won,
        shots_per_game = excluded.shots_per_game,
        tackles_per_game = excluded.tackles_per_game,
        fouls_drawn = excluded.fouls_drawn,
        sprint_speed_kmh = excluded.sprint_speed_kmh,
        acceleration = excluded.acceleration,
        stamina = excluded.stamina,
        recovery_rate = excluded.recovery_rate,
        contribution_to_build_up = excluded.contribution_to_build_up,
        defensive_transitions = excluded.defensive_transitions,
        raw_json = excluded.raw_json,
        updated_at = CURRENT_TIMESTAMP
      returning id
      `
    )
    .get(
      playerId,
      seasonYear,
      teamId,
      leagueId,
      toInt(season.appearances),
      toInt(season.goals),
      toInt(season.assists),
      toInt(season.minutes),
      typeof season.position === "string" ? season.position : null,
      toFloat(season.rating),
      toFloat(season.xG ?? season.xg),
      toFloat(season.xA ?? season.xa),
      toInt(season.key_passes),
      toInt(season.successful_dribbles),
      toInt(season.duels_won),
      toFloat(season.shots_per_game),
      toFloat(season.tackles_per_game),
      toInt(season.fouls_drawn),
      toFloat(physical.sprint_speed_kmh),
      typeof physical.acceleration === "string" ? physical.acceleration : null,
      typeof physical.stamina === "string" ? physical.stamina : null,
      typeof physical.recovery_rate === "string" ? physical.recovery_rate : null,
      typeof tactical.contribution_to_build_up === "string" ? tactical.contribution_to_build_up : null,
      typeof tactical.defensive_transitions === "string" ? tactical.defensive_transitions : null,
      JSON.stringify(season)
    ) as { id?: number } | undefined;

  if (row?.id) {
    return row.id;
  }

  const lookup = db
    .prepare(
      `
      select id
      from player_seasons
      where player_id = ? and season = ? and ifnull(team_id, '') = ifnull(?, '') and ifnull(league_id, '') = ifnull(?, '')
      `
    )
    .get(playerId, seasonYear, teamId, leagueId) as { id?: number } | undefined;

  if (!lookup?.id) {
    throw new Error(`Could not upsert season row for player ${playerId}, season ${seasonYear}`);
  }

  return lookup.id;
}

function replaceSeasonChildren(db: any, playerSeasonId: number, season: Dict): void {
  db.prepare("delete from season_national_stats where player_season_id = ?").run(playerSeasonId);
  db.prepare("delete from injuries where player_season_id = ?").run(playerSeasonId);
  db.prepare("delete from transfers where player_season_id = ?").run(playerSeasonId);

  const nationalStats = recordArray(season.national_team_stats);
  for (const nat of nationalStats) {
    const teamId = normalizeId(nat.team_id);
    ensureTeam(db, teamId);

    db.prepare(
      `
      insert into season_national_stats(
        player_season_id, team_id, competition, appearances, goals, assists,
        minutes, position, rating, raw_json
      )
      values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `
    ).run(
      playerSeasonId,
      teamId,
      typeof nat.competition === "string" ? nat.competition : null,
      toInt(nat.appearances),
      toInt(nat.goals),
      toInt(nat.assists),
      toInt(nat.minutes),
      typeof nat.position === "string" ? nat.position : null,
      toFloat(nat.rating),
      JSON.stringify(nat)
    );
  }

  const injuries = recordArray(season.injuries);
  for (const injury of injuries) {
    db.prepare(
      `
      insert into injuries(
        player_season_id, injury_type, start_date, end_date,
        days_lost, source, raw_json
      )
      values (?, ?, ?, ?, ?, ?, ?)
      `
    ).run(
      playerSeasonId,
      typeof injury.type === "string" ? injury.type : null,
      toDateString(injury.start_date),
      toDateString(injury.end_date),
      toInt(injury.days_lost),
      typeof injury.source === "string" ? injury.source : null,
      JSON.stringify(injury)
    );
  }

  const transfers = recordArray(season.transfer_history);
  for (const transfer of transfers) {
    const fromId = normalizeId(transfer.from);
    const toId = normalizeId(transfer.to);
    ensureTeam(db, fromId);
    ensureTeam(db, toId);

    db.prepare(
      `
      insert into transfers(
        player_season_id, from_team_id, to_team_id, transfer_fee,
        transfer_date, source, raw_json
      )
      values (?, ?, ?, ?, ?, ?, ?)
      `
    ).run(
      playerSeasonId,
      fromId,
      toId,
      typeof transfer.transfer_fee === "string" ? transfer.transfer_fee : null,
      toDateString(transfer.date ?? transfer.transfer_date),
      typeof transfer.source === "string" ? transfer.source : null,
      JSON.stringify(transfer)
    );
  }
}

export function importPlayerDocumentToSqlite(
  document: unknown,
  options: ImportOptions = {}
): PlayerImportResult {
  const overAgeThreshold = options.overAgeThreshold ?? 35;
  const parsed = asRecord(document);
  const player = asRecord(parsed.player);
  const teams = recordArray(parsed.teams);
  const seasons = recordArray(parsed.seasons);

  if (!Object.keys(player).length) {
    throw new Error("Invalid JSON: missing player object.");
  }

  return withSqliteDatabase(undefined, (db) => {
    db.exec("BEGIN");

    try {
      const playerId = upsertPlayer(db, player, seasons, overAgeThreshold);

      for (const team of teams) {
        const teamId = normalizeId(team.id);
        ensureTeam(db, teamId, team);
      }

      let importedSeasons = 0;
      for (const season of seasons) {
        const playerSeasonId = upsertPlayerSeason(db, playerId, season);
        replaceSeasonChildren(db, playerSeasonId, season);
        importedSeasons += 1;
      }

      db.exec("COMMIT");

      return {
        playerId,
        playerName: String(player.name || playerId),
        seasonsImported: importedSeasons,
      };
    } catch (error) {
      db.exec("ROLLBACK");
      throw error;
    }
  });
}
