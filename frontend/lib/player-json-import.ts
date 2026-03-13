import { supabaseRestRequest } from "@/lib/supabase-rest";

const UPSERT_HEADERS = {
  Prefer: "resolution=merge-duplicates,return=representation",
};

type Dict = Record<string, unknown>;

type ImportOptions = {
  overAgeThreshold?: number;
};

export type PlayerImportResult = {
  playerId: string;
  playerName: string;
  seasonsImported: number;
};

type SeasonValidationResult = {
  season: Dict;
  seasonYear: number;
  teamId: string;
};

const UNKNOWN_TEAM_ID = "unknown-team";
const UNKNOWN_TEAM_NAME = "Unknown Team";

function asRecord(value: unknown): Dict {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Dict) : {};
}

function recordArray(value: unknown): Dict[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map(asRecord).filter((entry) => Object.keys(entry).length > 0);
}

function toStringOrNull(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const clean = String(value).trim();
  return clean ? clean : null;
}

function normalizeId(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const clean = String(value).trim().toLowerCase();
  return clean ? clean : null;
}

function normalizeTeamId(value: unknown): string {
  return normalizeId(value) || UNKNOWN_TEAM_ID;
}

function normalizeSlug(value: unknown, fallback = "unknown"): string {
  const raw = String(value ?? "").trim().toLowerCase();
  if (!raw) {
    return fallback;
  }
  const slug = raw.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return slug || fallback;
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
  const isIsoDate = /^\d{4}-\d{2}-\d{2}$/.test(raw);
  return isIsoDate ? raw : null;
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

async function ensureTeam(teamId: string | null, team: Dict = {}): Promise<void> {
  if (!teamId) {
    return;
  }

  const nameFromFile = typeof team.name === "string" ? team.name.trim() : "";
  const row: Dict = {
    id: teamId,
    name: nameFromFile || titleFromId(teamId),
  };

  if (typeof team.country === "string" && team.country.trim()) {
    row.country = team.country;
  }
  if (typeof team.logo_url === "string" && team.logo_url.trim()) {
    row.logo_url = team.logo_url;
  }

  await supabaseRestRequest("teams", {
    method: "POST",
    params: { on_conflict: "id" },
    body: [row],
    extraHeaders: UPSERT_HEADERS,
  });
}

async function upsertPlayer(player: Dict, seasons: Dict[], overAgeThreshold: number): Promise<string> {
  const playerId = normalizeId(player.id);
  if (!playerId) {
    throw new Error("Missing player.id");
  }

  const row = {
    id: playerId,
    name: String(player.name || playerId),
    birth_date: toDateString(player.birth_date),
    nationality: typeof player.nationality === "string" ? player.nationality : null,
    height_cm: toInt(player.height_cm),
    weight_kg: toInt(player.weight_kg),
    dominant_foot: typeof player.dominant_foot === "string" ? player.dominant_foot : null,
    is_retired: parseRetired(player),
    over_35: computeOverAge(player, seasons, overAgeThreshold),
    retired_since: toDateString(player.retired_since),
  };

  await supabaseRestRequest("players", {
    method: "POST",
    params: { on_conflict: "id" },
    body: [row],
    extraHeaders: UPSERT_HEADERS,
  });

  return playerId;
}

async function upsertPlayerSeason(playerId: string, season: Dict): Promise<number> {
  const seasonYear = toInt(season.season);
  if (seasonYear === null) {
    throw new Error(`Missing or invalid season year for player ${playerId}`);
  }

  const teamId = normalizeTeamId(season.team_id);
  const leagueId = normalizeSlug(season.league_id, "unknown");
  const physical = asRecord(season.physical_metrics);
  const tactical = asRecord(season.tactical_data);

  await ensureTeam(teamId, teamId === UNKNOWN_TEAM_ID ? { name: UNKNOWN_TEAM_NAME } : {});

  const row = {
    player_id: playerId,
    season: seasonYear,
    team_id: teamId,
    league_id: leagueId,
    appearances: toInt(season.appearances),
    goals: toInt(season.goals),
    assists: toInt(season.assists),
    minutes: toInt(season.minutes),
    position: typeof season.position === "string" ? season.position : null,
    rating: toFloat(season.rating),
    xg: toFloat(season.xG ?? season.xg),
    xa: toFloat(season.xA ?? season.xa),
    key_passes: toInt(season.key_passes),
    successful_dribbles: toInt(season.successful_dribbles),
    duels_won: toInt(season.duels_won),
    shots_per_game: toFloat(season.shots_per_game),
    tackles_per_game: toFloat(season.tackles_per_game),
    fouls_drawn: toInt(season.fouls_drawn),
    sprint_speed_kmh: toFloat(physical.sprint_speed_kmh),
    acceleration: typeof physical.acceleration === "string" ? physical.acceleration : null,
    stamina: typeof physical.stamina === "string" ? physical.stamina : null,
    recovery_rate: typeof physical.recovery_rate === "string" ? physical.recovery_rate : null,
    contribution_to_build_up:
      typeof tactical.contribution_to_build_up === "string" ? tactical.contribution_to_build_up : null,
    defensive_transitions:
      typeof tactical.defensive_transitions === "string" ? tactical.defensive_transitions : null,
    raw_json: season,
  };

  const rows = await supabaseRestRequest("player_seasons", {
    method: "POST",
    params: {
      on_conflict: "player_id,season,team_id,league_id",
      select: "id",
    },
    body: [row],
    extraHeaders: UPSERT_HEADERS,
  });

  const seasonId = toInt((Array.isArray(rows) ? rows[0] : null)?.id);
  if (seasonId === null) {
    throw new Error(`Could not upsert season row for player ${playerId}, season ${seasonYear}`);
  }

  return seasonId;
}

async function replaceSeasonChildren(playerSeasonId: number, season: Dict): Promise<void> {
  const seasonFilter = { player_season_id: `eq.${playerSeasonId}` };

  await supabaseRestRequest("season_national_stats", { method: "DELETE", params: seasonFilter });
  await supabaseRestRequest("injuries", { method: "DELETE", params: seasonFilter });
  await supabaseRestRequest("transfers", { method: "DELETE", params: seasonFilter });

  const nationalStats = recordArray(season.national_team_stats);
  if (nationalStats.length) {
    const rows = [] as Dict[];
    for (const nat of nationalStats) {
      const teamId = normalizeId(nat.team_id);
      await ensureTeam(teamId);
      rows.push({
        player_season_id: playerSeasonId,
        team_id: teamId,
        competition: typeof nat.competition === "string" ? nat.competition : null,
        appearances: toInt(nat.appearances),
        goals: toInt(nat.goals),
        assists: toInt(nat.assists),
        minutes: toInt(nat.minutes),
        position: typeof nat.position === "string" ? nat.position : null,
        rating: toFloat(nat.rating),
        raw_json: nat,
      });
    }

    if (rows.length) {
      await supabaseRestRequest("season_national_stats", {
        method: "POST",
        body: rows,
      });
    }
  }

  const injuries = recordArray(season.injuries);
  if (injuries.length) {
    const rows = injuries.map((injury) => ({
      player_season_id: playerSeasonId,
      injury_type: typeof injury.type === "string" ? injury.type : null,
      start_date: toDateString(injury.start_date),
      end_date: toDateString(injury.end_date),
      days_lost: toInt(injury.days_lost),
      source: typeof injury.source === "string" ? injury.source : null,
      raw_json: injury,
    }));

    await supabaseRestRequest("injuries", {
      method: "POST",
      body: rows,
    });
  }

  const transfers = recordArray(season.transfer_history);
  if (transfers.length) {
    const rows = [] as Dict[];
    for (const transfer of transfers) {
      const fromId = normalizeId(transfer.from);
      const toId = normalizeId(transfer.to);
      await ensureTeam(fromId);
      await ensureTeam(toId);

      rows.push({
        player_season_id: playerSeasonId,
        from_team_id: fromId,
        to_team_id: toId,
        transfer_fee: typeof transfer.transfer_fee === "string" ? transfer.transfer_fee : null,
        transfer_date: toDateString(transfer.date ?? transfer.transfer_date),
        source: typeof transfer.source === "string" ? transfer.source : null,
        raw_json: transfer,
      });
    }

    if (rows.length) {
      await supabaseRestRequest("transfers", {
        method: "POST",
        body: rows,
      });
    }
  }
}

function expandSeasonRows(seasonInput: Dict): Dict[] {
  const seasonYear = toInt(seasonInput.season);
  if (seasonYear === null) {
    return [];
  }

  const seasonLevelNational = recordArray(seasonInput.national_team_stats);
  const seasonLevelInjuries = recordArray(seasonInput.injuries);
  const seasonLevelTransfers = recordArray(seasonInput.transfer_history);
  const seasonLevelPhysical = asRecord(seasonInput.physical_metrics);
  const seasonLevelTactical = asRecord(seasonInput.tactical_data);

  const rows: Dict[] = [];
  const teamEntries = recordArray(seasonInput.teams);

  for (const teamEntry of teamEntries) {
    const teamId = normalizeTeamId(teamEntry.team_id ?? seasonInput.team_id);
    const competitions = recordArray(teamEntry.competitions);
    const comps = competitions.length ? competitions : [{}];

    for (const comp of comps) {
      const competitionName = toStringOrNull(comp.competition);
      rows.push({
        ...comp,
        season: seasonYear,
        team_id: teamId,
        league_id: normalizeSlug(comp.league_id ?? competitionName ?? seasonInput.league_id, "unknown"),
        national_team_stats: recordArray(comp.national_team_stats).length
          ? recordArray(comp.national_team_stats)
          : seasonLevelNational,
        injuries: recordArray(comp.injuries).length ? recordArray(comp.injuries) : seasonLevelInjuries,
        transfer_history: recordArray(comp.transfer_history).length
          ? recordArray(comp.transfer_history)
          : seasonLevelTransfers,
        physical_metrics: Object.keys(asRecord(comp.physical_metrics)).length
          ? asRecord(comp.physical_metrics)
          : seasonLevelPhysical,
        tactical_data: Object.keys(asRecord(comp.tactical_data)).length
          ? asRecord(comp.tactical_data)
          : seasonLevelTactical,
      });
    }
  }

  if (rows.length) {
    return rows;
  }

  return [
    {
      ...seasonInput,
      season: seasonYear,
      team_id: normalizeTeamId(seasonInput.team_id),
      league_id: normalizeSlug(seasonInput.league_id, "unknown"),
      national_team_stats: seasonLevelNational,
      injuries: seasonLevelInjuries,
      transfer_history: seasonLevelTransfers,
      physical_metrics: seasonLevelPhysical,
      tactical_data: seasonLevelTactical,
    },
  ];
}

function validateSeasonDocument(seasonInput: unknown): SeasonValidationResult {
  const season = asRecord(seasonInput);
  if (!Object.keys(season).length) {
    throw new Error("Invalid season JSON: expected an object.");
  }

  const seasonYear = toInt(season.season);
  if (seasonYear === null || seasonYear < 1900 || seasonYear > 2200) {
    throw new Error("Invalid season JSON: 'season' must be a valid year.");
  }

  const teamId = normalizeId(season.team_id);
  if (!teamId) {
    throw new Error("Invalid season JSON: 'team_id' is required.");
  }

  const normalized: Dict = {
    ...season,
    season: seasonYear,
    team_id: teamId,
    league_id: normalizeId(season.league_id) || "unknown",
    position: toStringOrNull(season.position),
    appearances: toInt(season.appearances),
    goals: toInt(season.goals),
    assists: toInt(season.assists),
    minutes: toInt(season.minutes),
    rating: toFloat(season.rating),
    xG: toFloat(season.xG ?? season.xg),
    xA: toFloat(season.xA ?? season.xa),
    key_passes: toInt(season.key_passes),
    successful_dribbles: toInt(season.successful_dribbles),
    duels_won: toInt(season.duels_won),
    shots_per_game: toFloat(season.shots_per_game),
    tackles_per_game: toFloat(season.tackles_per_game),
    fouls_drawn: toInt(season.fouls_drawn),
    physical_metrics: asRecord(season.physical_metrics),
    tactical_data: asRecord(season.tactical_data),
    national_team_stats: recordArray(season.national_team_stats),
    injuries: recordArray(season.injuries),
    transfer_history: recordArray(season.transfer_history),
  };

  return {
    season: normalized,
    seasonYear,
    teamId,
  };
}

async function playerExists(playerId: string): Promise<boolean> {
  const rows = await supabaseRestRequest("players", {
    method: "GET",
    params: {
      select: "id",
      id: `eq.${playerId}`,
      limit: "1",
    },
  });

  return Array.isArray(rows) && rows.length > 0;
}

export async function upsertPlayerSeasonDocument(
  playerIdInput: unknown,
  seasonInput: unknown
): Promise<{ playerId: string; season: number; teamId: string }> {
  const playerId = normalizeId(playerIdInput);
  if (!playerId) {
    throw new Error("Missing or invalid player id.");
  }

  const exists = await playerExists(playerId);
  if (!exists) {
    throw new Error(`Player '${playerId}' was not found in database.`);
  }

  const validated = validateSeasonDocument(seasonInput);
  const playerSeasonId = await upsertPlayerSeason(playerId, validated.season);
  await replaceSeasonChildren(playerSeasonId, validated.season);

  return {
    playerId,
    season: validated.seasonYear,
    teamId: validated.teamId,
  };
}

export async function importPlayerDocument(
  document: unknown,
  options: ImportOptions = {}
): Promise<PlayerImportResult> {
  const overAgeThreshold = options.overAgeThreshold ?? 35;
  const parsed = asRecord(document);
  const player = asRecord(parsed.player);
  const teams = recordArray(parsed.teams);
  const seasons = recordArray(parsed.seasons);

  if (!Object.keys(player).length) {
    throw new Error("Invalid JSON: missing player object.");
  }

  const playerId = await upsertPlayer(player, seasons, overAgeThreshold);

  for (const team of teams) {
    const teamId = normalizeId(team.id);
    await ensureTeam(teamId, team);
  }

  let importedSeasons = 0;
  for (const season of seasons) {
    const expandedRows = expandSeasonRows(season);
    for (const seasonRow of expandedRows) {
      const playerSeasonId = await upsertPlayerSeason(playerId, seasonRow);
      await replaceSeasonChildren(playerSeasonId, seasonRow);
      importedSeasons += 1;
    }
  }

  return {
    playerId,
    playerName: String(player.name || playerId),
    seasonsImported: importedSeasons,
  };
}
