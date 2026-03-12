import crypto from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE_NAME = "proxima_admin_session";
const SESSION_TTL_SECONDS = 60 * 60 * 12;

type SessionPayload = {
  iat: number;
  exp: number;
};

function getAdminPassword(): string {
  const password = process.env.ADMIN_DASHBOARD_PASSWORD;
  if (!password) {
    throw new Error("Missing ADMIN_DASHBOARD_PASSWORD.");
  }
  return password;
}

function getSessionSecret(): string {
  const secret = process.env.ADMIN_SESSION_SECRET;
  if (!secret) {
    throw new Error("Missing ADMIN_SESSION_SECRET.");
  }
  return secret;
}

function signPayload(payload: string, secret: string): string {
  return crypto.createHmac("sha256", secret).update(payload).digest("base64url");
}

function encodeSession(payload: SessionPayload, secret: string): string {
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = signPayload(encodedPayload, secret);
  return `${encodedPayload}.${signature}`;
}

function decodeSession(token: string, secret: string): SessionPayload | null {
  const [encodedPayload, signature] = token.split(".");
  if (!encodedPayload || !signature) {
    return null;
  }

  const expectedSignature = signPayload(encodedPayload, secret);
  const provided = Buffer.from(signature);
  const expected = Buffer.from(expectedSignature);

  if (provided.length !== expected.length) {
    return null;
  }
  if (!crypto.timingSafeEqual(provided, expected)) {
    return null;
  }

  try {
    const payload = JSON.parse(Buffer.from(encodedPayload, "base64url").toString("utf-8"));
    if (
      typeof payload?.iat !== "number" ||
      typeof payload?.exp !== "number" ||
      payload.exp <= Math.floor(Date.now() / 1000)
    ) {
      return null;
    }
    return payload as SessionPayload;
  } catch {
    return null;
  }
}

export function hasAdminAuthConfig(): boolean {
  return Boolean(process.env.ADMIN_DASHBOARD_PASSWORD && process.env.ADMIN_SESSION_SECRET);
}

export function verifyAdminPassword(candidate: string): boolean {
  const expected = Buffer.from(getAdminPassword());
  const actual = Buffer.from(candidate ?? "");
  if (expected.length !== actual.length) {
    return false;
  }
  return crypto.timingSafeEqual(expected, actual);
}

export function setAdminSessionCookie(response: NextResponse): void {
  const now = Math.floor(Date.now() / 1000);
  const token = encodeSession({ iat: now, exp: now + SESSION_TTL_SECONDS }, getSessionSecret());

  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: token,
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
}

export function clearAdminSessionCookie(response: NextResponse): void {
  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: "",
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
}

export function isAdminAuthenticated(request: NextRequest): boolean {
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!token) {
    return false;
  }
  const payload = decodeSession(token, getSessionSecret());
  return Boolean(payload);
}
