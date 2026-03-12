import { getDatabaseProvider, isSQLiteProvider } from "@/lib/database-provider";
import { hasAdminAuthConfig, isAdminAuthenticated } from "@/lib/admin-auth";
import { triggerPredictionWorkflow } from "@/lib/github-actions";
import { NextRequest, NextResponse } from "next/server";

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

  if (isSQLiteProvider()) {
    return NextResponse.json(
      {
        error:
          "SQLite mode does not dispatch remote GitHub prediction runs. Run backend/python/main_sqlite.py locally.",
        provider,
      },
      { status: 400 }
    );
  }

  try {
    const result = await triggerPredictionWorkflow();
    return NextResponse.json({
      ok: true,
      provider,
      message: "Workflow dispatched successfully.",
      actionsUrl: result.actionsUrl,
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Failed to trigger workflow dispatch.", provider },
      { status: 500 }
    );
  }
}
