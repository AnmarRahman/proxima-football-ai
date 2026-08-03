import { hasAdminAuthConfig, isAdminAuthenticated } from "@/lib/admin-auth";
import { hasSupabaseServerConfig, supabaseRestGet } from "@/lib/supabase-rest";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  if (!hasAdminAuthConfig()) {
    return NextResponse.json({ error: "Admin auth is not configured." }, { status: 500 });
  }
  if (!isAdminAuthenticated(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!hasSupabaseServerConfig()) {
    return NextResponse.json({ error: "Supabase server configuration is missing." }, { status: 500 });
  }

  try {
    const [models, runs, predictions] = await Promise.all([
      supabaseRestGet("model_versions", {
        select: "version,data_version,manifest_sha256,approved,trained_at,updated_at",
        approved: "eq.true",
        order: "updated_at.desc",
        limit: "5",
      }),
      supabaseRestGet("tier_a_prediction_runs", {
        select: "id,status,run_type,triggered_by,model_version,started_at,ended_at,predicted_count,rejected_count,error_message",
        order: "started_at.desc",
        limit: "10",
      }),
      supabaseRestGet("next_season_predictions", {
        select: "player_id",
        limit: "1000",
      }),
    ]);
    return NextResponse.json({
      approvedModels: models || [],
      recentRuns: runs || [],
      predictionCount: Array.isArray(predictions) ? predictions.length : 0,
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Failed to load Tier A prediction status." },
      { status: 500 }
    );
  }
}
