import { getDatabaseProvider } from "@/lib/database-provider";
import { hasAdminAuthConfig, isAdminAuthenticated } from "@/lib/admin-auth";
import { hasSupabaseServerConfig } from "@/lib/supabase-rest";
import { upsertPlayerSeasonDocument } from "@/lib/player-json-import";
import { NextRequest, NextResponse } from "next/server";

type SaveSeasonRequest = {
  playerId?: unknown;
  mode?: unknown;
  season?: unknown;
  seasonJson?: unknown;
};

function isClientInputError(message: string): boolean {
  return [
    "Invalid request body",
    "Missing playerId",
    "Invalid mode",
    "Missing season",
    "Invalid season JSON",
    "Missing or invalid player id",
    "was not found in database",
  ].some((prefix) => message.startsWith(prefix));
}

function parseRequestBody(raw: unknown): { playerId: unknown; season: unknown; mode: "manual" | "json" } {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("Invalid request body.");
  }

  const body = raw as SaveSeasonRequest;
  const playerId = body.playerId;
  if (playerId === null || playerId === undefined || String(playerId).trim() === "") {
    throw new Error("Missing playerId.");
  }

  const modeRaw = String(body.mode ?? "manual").trim().toLowerCase();
  if (modeRaw !== "manual" && modeRaw !== "json") {
    throw new Error("Invalid mode. Use 'manual' or 'json'.");
  }

  if (modeRaw === "manual") {
    if (!body.season || typeof body.season !== "object" || Array.isArray(body.season)) {
      throw new Error("Missing season object for manual mode.");
    }
    return { playerId, season: body.season, mode: "manual" };
  }

  const seasonJson = String(body.seasonJson ?? "").trim();
  if (!seasonJson) {
    throw new Error("Missing seasonJson for json mode.");
  }

  try {
    const parsed = JSON.parse(seasonJson);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Invalid season JSON: expected a JSON object.");
    }
    return { playerId, season: parsed, mode: "json" };
  } catch (error: any) {
    if (error?.message?.startsWith("Invalid season JSON:")) {
      throw error;
    }
    throw new Error(`Invalid season JSON: ${error?.message || "Unable to parse."}`);
  }
}

export async function POST(request: NextRequest) {
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
          "Database REST config is missing for the selected provider. Set POSTGREST_URL for postgres mode, or NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY for supabase mode.",
      },
      { status: 500 }
    );
  }

  const provider = getDatabaseProvider();

  try {
    const payload = parseRequestBody(await request.json());
    const result = await upsertPlayerSeasonDocument(payload.playerId, payload.season);

    return NextResponse.json({
      ok: true,
      provider,
      mode: payload.mode,
      playerId: result.playerId,
      season: result.season,
      teamId: result.teamId,
      message: "Season saved successfully.",
    });
  } catch (error: any) {
    const message = String(error?.message || "Failed to save season.");
    return NextResponse.json(
      {
        error: message,
        provider,
      },
      { status: isClientInputError(message) ? 400 : 500 }
    );
  }
}
