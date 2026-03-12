import { getDatabaseProvider, isSQLiteProvider } from "@/lib/database-provider";
import { hasSupabaseServerConfig, supabaseRestGet } from "@/lib/supabase-rest";
import { sqliteGet } from "@/lib/sqlite-db";
import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

function sanitizePlayerId(raw: string): string | null {
  const clean = String(raw || "").trim().toLowerCase();
  if (!/^[a-z0-9-]+$/.test(clean)) {
    return null;
  }
  return clean;
}

async function readLocalFallbackPrediction(playerId: string): Promise<any[] | null> {
  const filePath = path.join(process.cwd(), "public", "data", "predictions", `${playerId}.json`);
  try {
    const content = await fs.readFile(filePath, "utf-8");
    const parsed = JSON.parse(content);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function parsePredictionJson(raw: unknown): any[] {
  if (Array.isArray(raw)) {
    return raw;
  }
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

export async function GET(
  _request: Request,
  context: { params: { playerId: string } }
) {
  const provider = getDatabaseProvider();
  const playerId = sanitizePlayerId(context.params.playerId);
  if (!playerId) {
    return NextResponse.json({ error: "Invalid player id" }, { status: 400 });
  }

  if (isSQLiteProvider()) {
    try {
      const prediction = sqliteGet<{
        run_id: string;
        predicted_at: string;
        horizon_seasons: number;
        prediction_json: unknown;
        confidence_score: number | null;
        player_name: string | null;
      }>(
        `
        select
          pp.run_id,
          pp.predicted_at,
          pp.horizon_seasons,
          pp.prediction_json,
          pp.confidence_score,
          p.name as player_name
        from player_predictions pp
        join prediction_runs pr on pr.id = pp.run_id and pr.status = 'success'
        left join players p on p.id = pp.player_id
        where pp.player_id = ?
        order by pp.predicted_at desc, pp.id desc
        limit 1
        `,
        [playerId]
      );

      if (!prediction) {
        const fallback = await readLocalFallbackPrediction(playerId);
        if (!fallback) {
          return NextResponse.json({ error: "Prediction not found" }, { status: 404 });
        }

        return NextResponse.json({
          player: { id: playerId, name: playerId },
          stats: fallback,
          source: "fallback",
          provider,
        });
      }

      return NextResponse.json({
        player: {
          id: playerId,
          name: prediction.player_name || playerId,
        },
        stats: parsePredictionJson(prediction.prediction_json),
        meta: {
          run_id: prediction.run_id,
          predicted_at: prediction.predicted_at,
          horizon_seasons: prediction.horizon_seasons,
          confidence_score: prediction.confidence_score,
        },
        source: "sqlite",
        provider,
      });
    } catch (error: any) {
      const fallback = await readLocalFallbackPrediction(playerId);
      if (fallback) {
        return NextResponse.json({
          player: { id: playerId, name: playerId },
          stats: fallback,
          source: "fallback",
          provider,
          error: error?.message || "SQLite query failed",
        });
      }

      return NextResponse.json(
        { error: error?.message || "Failed to fetch prediction" },
        { status: 500 }
      );
    }
  }

  if (!hasSupabaseServerConfig()) {
    const fallback = await readLocalFallbackPrediction(playerId);
    if (!fallback) {
      return NextResponse.json({ error: "Prediction not found" }, { status: 404 });
    }

    return NextResponse.json({
      player: { id: playerId, name: playerId },
      stats: fallback,
      source: "fallback",
      provider,
    });
  }

  try {
    const [predictionRows, playerRows] = await Promise.all([
      supabaseRestGet("latest_player_predictions", {
        select: "player_id,run_id,predicted_at,horizon_seasons,prediction_json,confidence_score",
        player_id: `eq.${playerId}`,
        limit: "1",
      }),
      supabaseRestGet("players", {
        select: "id,name",
        id: `eq.${playerId}`,
        limit: "1",
      }),
    ]);

    const prediction = (predictionRows || [])[0];
    const player = (playerRows || [])[0];

    if (!prediction) {
      const fallback = await readLocalFallbackPrediction(playerId);
      if (!fallback) {
        return NextResponse.json({ error: "Prediction not found" }, { status: 404 });
      }

      return NextResponse.json({
        player: { id: playerId, name: player?.name || playerId },
        stats: fallback,
        source: "fallback",
        provider,
      });
    }

    const stats = Array.isArray(prediction.prediction_json)
      ? prediction.prediction_json
      : [];

    return NextResponse.json({
      player: {
        id: playerId,
        name: player?.name || playerId,
      },
      stats,
      meta: {
        run_id: prediction.run_id,
        predicted_at: prediction.predicted_at,
        horizon_seasons: prediction.horizon_seasons,
        confidence_score: prediction.confidence_score,
      },
      source: "database",
      provider,
    });
  } catch (error: any) {
    const fallback = await readLocalFallbackPrediction(playerId);
    if (fallback) {
      return NextResponse.json({
        player: { id: playerId, name: playerId },
        stats: fallback,
        source: "fallback",
        provider,
        error: error?.message || "DB query failed",
      });
    }

    return NextResponse.json(
      { error: error?.message || "Failed to fetch prediction" },
      { status: 500 }
    );
  }
}
