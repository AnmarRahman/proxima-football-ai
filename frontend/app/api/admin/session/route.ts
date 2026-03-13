import { getDatabaseProvider } from "@/lib/database-provider";
import { hasAdminAuthConfig, isAdminAuthenticated } from "@/lib/admin-auth";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(request: NextRequest) {
  const provider = getDatabaseProvider();

  if (!hasAdminAuthConfig()) {
    return NextResponse.json({ authenticated: false, configured: false, provider }, { status: 200 });
  }

  return NextResponse.json({
    authenticated: isAdminAuthenticated(request),
    configured: true,
    provider,
  });
}
