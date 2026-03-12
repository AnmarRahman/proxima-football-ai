import {
  hasAdminAuthConfig,
  setAdminSessionCookie,
  verifyAdminPassword,
} from "@/lib/admin-auth";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  if (!hasAdminAuthConfig()) {
    return NextResponse.json(
      { error: "Admin auth is not configured on the server." },
      { status: 500 }
    );
  }

  let body: any;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const password = String(body?.password || "");
  if (!verifyAdminPassword(password)) {
    return NextResponse.json({ error: "Invalid admin password." }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  setAdminSessionCookie(response);
  return response;
}
