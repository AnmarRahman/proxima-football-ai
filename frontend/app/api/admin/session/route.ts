import { hasAdminAuthConfig, isAdminAuthenticated } from "@/lib/admin-auth";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  if (!hasAdminAuthConfig()) {
    return NextResponse.json({ authenticated: false, configured: false }, { status: 200 });
  }

  return NextResponse.json({
    authenticated: isAdminAuthenticated(request),
    configured: true,
  });
}
