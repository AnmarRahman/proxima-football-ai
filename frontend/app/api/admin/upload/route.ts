import { getDatabaseProvider } from "@/lib/database-provider";
import { hasAdminAuthConfig, isAdminAuthenticated } from "@/lib/admin-auth";
import { importPlayerDocument } from "@/lib/player-json-import";
import { hasSupabaseServerConfig } from "@/lib/supabase-rest";
import { NextRequest, NextResponse } from "next/server";

type FileResult = {
  file: string;
  playerId?: string;
  seasonsImported?: number;
  error?: string;
};

function parseThreshold(raw: FormDataEntryValue | null): number {
  const parsed = Number(raw ?? "35");
  if (!Number.isFinite(parsed)) {
    return 35;
  }
  return Math.max(1, Math.trunc(parsed));
}

function extractJsonFiles(formData: FormData): File[] {
  const directFiles = formData.getAll("files").filter((value): value is File => value instanceof File);
  if (directFiles.length) {
    return directFiles;
  }

  return Array.from(formData.values()).filter((value): value is File => value instanceof File);
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

  const provider = getDatabaseProvider();

  if (!hasSupabaseServerConfig()) {
    return NextResponse.json(
      {
        error:
          "Database REST config is missing for the selected provider. Set POSTGREST_URL for postgres mode, or NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY for supabase mode.",
      },
      { status: 500 }
    );
  }

  const formData = await request.formData();
  const files = extractJsonFiles(formData);
  const overAgeThreshold = parseThreshold(formData.get("overAgeThreshold"));

  if (!files.length) {
    return NextResponse.json({ error: "No JSON files uploaded." }, { status: 400 });
  }

  const successes: FileResult[] = [];
  const failures: FileResult[] = [];

  for (const file of files) {
    try {
      const raw = (await file.text()).replace(/^\uFEFF/, "");
      const parsed = JSON.parse(raw);

      const result = await importPlayerDocument(parsed, { overAgeThreshold });

      successes.push({
        file: file.name,
        playerId: result.playerId,
        seasonsImported: result.seasonsImported,
      });
    } catch (error: any) {
      failures.push({
        file: file.name,
        error: error?.message || "Unknown error",
      });
    }
  }

  return NextResponse.json({
    ok: failures.length === 0,
    provider,
    overAgeThreshold,
    totals: {
      filesReceived: files.length,
      imported: successes.length,
      failed: failures.length,
    },
    successes,
    failures,
  });
}
