import { supabaseRestGet, supabaseRestRequest } from "@/lib/supabase-rest";

type TierAImportResult = { playerId: string; seasonsImported: number; importKind: "tier-a" };

function record(value: unknown): Record<string, any> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Tier A player JSON must be an object.");
  }
  return value as Record<string, any>;
}

function requiredString(value: unknown, field: string): string {
  const clean = String(value || "").trim();
  if (!clean) throw new Error(`Tier A JSON is missing ${field}.`);
  return clean;
}

function number(value: unknown, field: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) throw new Error(`Invalid Tier A ${field}.`);
  return Math.trunc(parsed);
}

function boolean(value: unknown, field: string, defaultValue?: boolean): boolean {
  if (value === undefined && defaultValue !== undefined) return defaultValue;
  if (typeof value !== "boolean") throw new Error(`Tier A ${field} must be a boolean.`);
  return value;
}

export function isTierAPlayerDocument(value: unknown): boolean {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const doc = value as Record<string, any>;
  return Boolean(doc.player_id && doc.stat_scope === "domestic_league" && Array.isArray(doc.seasons));
}

export async function importTierAPlayerDocument(value: unknown): Promise<TierAImportResult> {
  const doc = record(value);
  const playerId = requiredString(doc.player_id, "player_id").toLowerCase();
  if (!/^[a-z0-9-]+$/.test(playerId)) throw new Error("Tier A player_id must use lowercase letters, numbers, and hyphens.");
  const coarseGroup = requiredString(doc.coarse_group, "coarse_group");
  if (!["DEF", "MID", "WIDE", "FWD", "GK"].includes(coarseGroup)) {
    throw new Error("Tier A coarse_group must be DEF, MID, WIDE, FWD, or GK.");
  }
  const careerStatus = requiredString(doc.career_status, "career_status");
  if (!["active", "retired", "inactive", "unknown"].includes(careerStatus)) {
    throw new Error("Tier A career_status is invalid.");
  }
  const birthDate = requiredString(doc.birth_date, "birth_date");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) {
    throw new Error("Tier A birth_date must use YYYY-MM-DD.");
  }

  const grouped = new Map<string, any>();
  for (const rawSeason of doc.seasons) {
    const season = record(rawSeason);
    if (season.stat_scope && season.stat_scope !== "domestic_league") {
      throw new Error("Tier A seasons cannot mix statistic scopes.");
    }
    const canonical = requiredString(season.canonical_season, "seasons[].canonical_season");
    const existing = grouped.get(canonical);
    const startYear = number(season.season_start_year ?? season.season, "season_start_year");
    const endYear = number(season.season_end_year ?? season.season, "season_end_year");
    if (endYear < startYear) throw new Error(`Tier A ${canonical} ends before it starts.`);
    const seasonFormat = requiredString(season.season_format, "season_format");
    if (!["split_year", "calendar_year"].includes(seasonFormat)) {
      throw new Error("Tier A season_format must be split_year or calendar_year.");
    }
    const normalized = {
      player_id: playerId,
      canonical_season: canonical,
      season_start_year: startYear,
      season_end_year: endYear,
      season_format: seasonFormat,
      appearances: number(season.appearances, "appearances"),
      goals: number(season.goals, "goals"),
      is_partial: boolean(season.is_partial, "is_partial", false),
      model_eligible: boolean(season.model_eligible, "model_eligible", true),
      source_row: season,
    };
    if (existing) {
      if (
        existing.season_start_year !== normalized.season_start_year ||
        existing.season_end_year !== normalized.season_end_year ||
        existing.season_format !== normalized.season_format
      ) {
        throw new Error(`Tier A duplicate season ${canonical} has inconsistent chronology.`);
      }
      existing.appearances += normalized.appearances;
      existing.goals += normalized.goals;
      existing.is_partial = existing.is_partial || normalized.is_partial;
      existing.model_eligible = existing.model_eligible && normalized.model_eligible;
      existing.source_row = { aggregated_rows: [existing.source_row, normalized.source_row] };
    } else {
      grouped.set(canonical, normalized);
    }
  }
  if (!grouped.size) throw new Error("Tier A JSON has no seasons.");

  await supabaseRestRequest("ml_players", {
    method: "POST",
    params: { on_conflict: "id" },
    extraHeaders: { Prefer: "resolution=merge-duplicates" },
    body: [{
      id: playerId,
      name: requiredString(doc.name, "name"),
      birth_date: birthDate,
      nationality: doc.nationality || null,
      primary_position: doc.primary_position || null,
      position_group: doc.position_group || null,
      coarse_group: coarseGroup,
      career_status: careerStatus,
      stat_scope: "domestic_league",
      updated_at: new Date().toISOString(),
    }],
  });

  await supabaseRestRequest("ml_player_seasons", {
    method: "POST",
    params: { on_conflict: "player_id,canonical_season" },
    extraHeaders: { Prefer: "resolution=merge-duplicates" },
    body: Array.from(grouped.values()).map((season) => ({
      ...season,
      updated_at: new Date().toISOString(),
    })),
  });

  const storedRows = await supabaseRestGet("ml_player_seasons", {
    select: "canonical_season",
    player_id: `eq.${playerId}`,
  });
  for (const stored of storedRows || []) {
    const canonicalSeason = String(stored.canonical_season);
    if (!grouped.has(canonicalSeason)) {
      await supabaseRestRequest("ml_player_seasons", {
        method: "DELETE",
        params: {
          player_id: `eq.${playerId}`,
          canonical_season: `eq.${canonicalSeason}`,
        },
      });
    }
  }

  return { playerId, seasonsImported: grouped.size, importKind: "tier-a" };
}
