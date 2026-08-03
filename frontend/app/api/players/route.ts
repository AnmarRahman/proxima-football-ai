import { hasSupabaseServerConfig, supabaseRestGet } from "@/lib/supabase-rest";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!hasSupabaseServerConfig()) {
    return NextResponse.json(
      { players: [], source: "unavailable", error: "Prediction database is not configured." },
      { status: 503 }
    );
  }

  try {
    const [playerRows, predictionRows] = await Promise.all([
      supabaseRestGet("ml_players", {
        select: "id,name,nationality,primary_position,coarse_group,career_status",
        career_status: "eq.active",
        order: "name.asc",
        limit: "1000",
      }),
      supabaseRestGet("next_season_predictions", {
        select: "player_id,predicted_season,predicted_at,model_version",
        limit: "1000",
      }),
    ]);

    const predictions = new Map(
      (predictionRows || []).map((row: any) => [String(row.player_id), row])
    );
    const players = (playerRows || [])
      .filter((row: any) => predictions.has(String(row.id)))
      .map((row: any) => {
        const prediction: any = predictions.get(String(row.id));
        return {
          id: String(row.id),
          name: String(row.name),
          nationality: row.nationality || null,
          position: row.primary_position || null,
          coarse_group: row.coarse_group || null,
          predicted_season: prediction?.predicted_season || null,
          model_version: prediction?.model_version || null,
          predicted_at: prediction?.predicted_at || null,
        };
      });

    return NextResponse.json({ players, source: "database" });
  } catch (error: any) {
    return NextResponse.json(
      { players: [], source: "database", error: error?.message || "Failed to query Supabase" },
      { status: 500 }
    );
  }
}
