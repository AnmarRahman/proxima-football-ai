import { hasAdminAuthConfig, isAdminAuthenticated } from "@/lib/admin-auth";
import { hasSupabaseServerConfig, supabaseRestGet } from "@/lib/supabase-rest";
import { NextRequest, NextResponse } from "next/server";

type PlayerRow = {
  id: string;
  name: string;
  nationality?: string | null;
  birth_date?: string | null;
  is_retired?: boolean | null;
  over_35?: boolean | null;
  retired_since?: string | null;
};

type SeasonRow = {
  player_id: string;
  season: number | string;
  team_id?: string | null;
  league_id?: string | null;
  appearances?: number | string | null;
  goals?: number | string | null;
  assists?: number | string | null;
  minutes?: number | string | null;
  rating?: number | string | null;
};

function toNumber(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

async function fetchAllPlayers(): Promise<PlayerRow[]> {
  const pageSize = 1000;
  const all: PlayerRow[] = [];
  let offset = 0;

  while (true) {
    const rows = (await supabaseRestGet("players", {
      select: "id,name,nationality,birth_date,is_retired,over_35,retired_since",
      order: "name.asc",
      limit: String(pageSize),
      offset: String(offset),
    })) as PlayerRow[];

    if (!Array.isArray(rows) || rows.length === 0) {
      break;
    }

    all.push(...rows);

    if (rows.length < pageSize) {
      break;
    }

    offset += rows.length;
  }

  return all;
}

async function fetchAllSeasons(): Promise<SeasonRow[]> {
  const pageSize = 1000;
  const all: SeasonRow[] = [];
  let offset = 0;

  while (true) {
    const rows = (await supabaseRestGet("player_seasons", {
      select: "player_id,season,team_id,league_id,appearances,goals,assists,minutes,rating",
      order: "player_id.asc,season.desc",
      limit: String(pageSize),
      offset: String(offset),
    })) as SeasonRow[];

    if (!Array.isArray(rows) || rows.length === 0) {
      break;
    }

    all.push(...rows);

    if (rows.length < pageSize) {
      break;
    }

    offset += rows.length;
  }

  return all;
}

export async function GET(request: NextRequest) {
  if (!hasAdminAuthConfig()) {
    return NextResponse.json(
      { error: "Admin auth is not configured on the server." },
      { status: 500 }
    );
  }

  if (!isAdminAuthenticated(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!hasSupabaseServerConfig()) {
    return NextResponse.json(
      {
        error:
          "Supabase server config is missing. Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
      },
      { status: 500 }
    );
  }

  try {
    const [players, seasons] = await Promise.all([fetchAllPlayers(), fetchAllSeasons()]);

    const seasonsByPlayer = new Map<string, SeasonRow[]>();
    for (const season of seasons) {
      const playerId = String(season.player_id || "").trim();
      if (!playerId) {
        continue;
      }
      const arr = seasonsByPlayer.get(playerId) || [];
      arr.push(season);
      seasonsByPlayer.set(playerId, arr);
    }

    const payload = players.map((player) => {
      const playerId = String(player.id || "").trim();
      const playerSeasons = (seasonsByPlayer.get(playerId) || [])
        .slice()
        .sort((a, b) => toNumber(b.season) - toNumber(a.season));

      const totals = playerSeasons.reduce(
        (acc, season) => {
          acc.appearances += toNumber(season.appearances);
          acc.goals += toNumber(season.goals);
          acc.assists += toNumber(season.assists);
          acc.minutes += toNumber(season.minutes);
          return acc;
        },
        { appearances: 0, goals: 0, assists: 0, minutes: 0 }
      );

      const latest = playerSeasons[0] || null;

      return {
        id: playerId,
        name: String(player.name || playerId),
        nationality: player.nationality || null,
        birth_date: player.birth_date || null,
        is_retired: Boolean(player.is_retired),
        over_35: Boolean(player.over_35),
        retired_since: player.retired_since || null,
        season_count: playerSeasons.length,
        career_totals: totals,
        latest_season: latest
          ? {
              season: toNumber(latest.season),
              team_id: latest.team_id || null,
              league_id: latest.league_id || null,
              appearances: toNumber(latest.appearances),
              goals: toNumber(latest.goals),
              assists: toNumber(latest.assists),
              minutes: toNumber(latest.minutes),
              rating: latest.rating === null || latest.rating === undefined ? null : Number(latest.rating),
            }
          : null,
        seasons: playerSeasons.map((season) => ({
          season: toNumber(season.season),
          team_id: season.team_id || null,
          league_id: season.league_id || null,
          appearances: toNumber(season.appearances),
          goals: toNumber(season.goals),
          assists: toNumber(season.assists),
          minutes: toNumber(season.minutes),
          rating: season.rating === null || season.rating === undefined ? null : Number(season.rating),
        })),
      };
    });

    return NextResponse.json({
      players: payload,
      totals: {
        players: payload.length,
        seasons: seasons.length,
      },
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Failed to load database data." },
      { status: 500 }
    );
  }
}
