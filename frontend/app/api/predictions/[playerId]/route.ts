import { hasSupabaseServerConfig, supabaseRestGet } from "@/lib/supabase-rest";
import { normalizePosition } from "@/lib/player-position";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function sanitizePlayerId(raw: string): string | null {
  const clean = String(raw || "").trim().toLowerCase();
  return /^[a-z0-9-]+$/.test(clean) ? clean : null;
}

export async function GET(
  _request: Request,
  context: { params: { playerId: string } }
) {
  const playerId = sanitizePlayerId(context.params.playerId);
  if (!playerId) {
    return NextResponse.json({ error: "Invalid player id" }, { status: 400 });
  }
  if (!hasSupabaseServerConfig()) {
    return NextResponse.json(
      { error: "Prediction database is not configured." },
      { status: 503 }
    );
  }

  try {
    const [predictionRows, playerRows, seasonRows] = await Promise.all([
      supabaseRestGet("next_season_predictions", {
        select:
          "player_id,run_id,model_version,prediction_scope,prediction_point,based_on_season,predicted_season,appearances_expected,appearances_lower,appearances_upper,appearances_interval_method,appearances_interval_unavailable_reason,goals_expected,goals_lower,goals_upper,goals_interval_method,limitations,coverage_metadata,predicted_at",
        player_id: `eq.${playerId}`,
        limit: "1",
      }),
      supabaseRestGet("ml_players", {
        select: "id,name,nationality,primary_position,position_group,coarse_group,career_status",
        id: `eq.${playerId}`,
        limit: "1",
      }),
      supabaseRestGet("ml_player_seasons", {
        select:
          "canonical_season,season_start_year,season_end_year,appearances,goals,is_partial,model_eligible",
        player_id: `eq.${playerId}`,
        order: "season_start_year.asc,season_end_year.asc",
        limit: "100",
      }),
    ]);

    const prediction = (predictionRows || [])[0];
    const player = (playerRows || [])[0];
    if (!prediction || !player) {
      return NextResponse.json({ error: "Next-season prediction not found" }, { status: 404 });
    }

    return NextResponse.json({
      player: {
        id: String(player.id),
        name: String(player.name),
        nationality: player.nationality || null,
        primary_position: normalizePosition(
          player.position_group,
          player.primary_position,
          player.coarse_group
        ),
        position_group: player.position_group || null,
        coarse_group: player.coarse_group || null,
        career_status: player.career_status,
      },
      prediction: {
        scope: prediction.prediction_scope,
        point: prediction.prediction_point,
        based_on_season: prediction.based_on_season,
        predicted_season: prediction.predicted_season,
        appearances: {
          expected: Number(prediction.appearances_expected),
          interval:
            prediction.appearances_lower === null || prediction.appearances_upper === null
              ? null
              : {
                  lower: Number(prediction.appearances_lower),
                  upper: Number(prediction.appearances_upper),
                  method: prediction.appearances_interval_method || null,
                },
          interval_unavailable_reason:
            prediction.appearances_interval_unavailable_reason || null,
        },
        goals: {
          expected: Number(prediction.goals_expected),
          interval:
            prediction.goals_lower === null || prediction.goals_upper === null
              ? null
              : {
                  lower: Number(prediction.goals_lower),
                  upper: Number(prediction.goals_upper),
                  method: prediction.goals_interval_method || null,
                },
        },
        limitations: Array.isArray(prediction.limitations) ? prediction.limitations : [],
        coverage_metadata: prediction.coverage_metadata || {},
      },
      historical_seasons: (seasonRows || []).map((season: any) => ({
        season: String(season.canonical_season),
        season_start_year: Number(season.season_start_year),
        season_end_year: Number(season.season_end_year),
        appearances: season.appearances === null ? null : Number(season.appearances),
        goals: season.goals === null ? null : Number(season.goals),
        is_partial: Boolean(season.is_partial),
        model_eligible: Boolean(season.model_eligible),
      })),
      meta: {
        run_id: prediction.run_id,
        model_version: prediction.model_version,
        predicted_at: prediction.predicted_at,
      },
      source: "database",
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Failed to fetch next-season prediction" },
      { status: 500 }
    );
  }
}
