import { isPostgresProvider } from "@/lib/database-provider";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

const POSTGREST_URL = process.env.POSTGREST_URL;
const POSTGREST_API_KEY = process.env.POSTGREST_API_KEY;

export type SupabaseRestRequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  params?: Record<string, string>;
  body?: unknown;
  extraHeaders?: Record<string, string>;
};

type RestConfig = {
  baseUrl: string;
  pathPrefix: string;
  defaultHeaders: Record<string, string>;
};

function hasPostgresRestConfig(): boolean {
  return Boolean(POSTGREST_URL);
}

function hasSupabaseConfig(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY);
}

export function hasSupabaseServerConfig(): boolean {
  return isPostgresProvider() ? hasPostgresRestConfig() : hasSupabaseConfig();
}

export function getSupabaseServerConfig(): { url: string; serviceRoleKey: string } {
  if (isPostgresProvider()) {
    if (!POSTGREST_URL) {
      throw new Error("Missing PostgREST server configuration.");
    }

    return {
      url: POSTGREST_URL,
      serviceRoleKey: POSTGREST_API_KEY || "",
    };
  }

  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("Missing Supabase server configuration.");
  }

  return { url: SUPABASE_URL, serviceRoleKey: SUPABASE_SERVICE_ROLE_KEY };
}

function getRestConfig(): RestConfig {
  if (isPostgresProvider()) {
    if (!POSTGREST_URL) {
      throw new Error("Missing PostgREST server configuration. Set POSTGREST_URL.");
    }

    const headers: Record<string, string> = {};
    if (POSTGREST_API_KEY) {
      headers.Authorization = `Bearer ${POSTGREST_API_KEY}`;
    }

    return {
      baseUrl: POSTGREST_URL,
      pathPrefix: "",
      defaultHeaders: headers,
    };
  }

  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("Missing Supabase server configuration.");
  }

  return {
    baseUrl: SUPABASE_URL,
    pathPrefix: "/rest/v1",
    defaultHeaders: {
      apikey: SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    },
  };
}

function buildEndpoint(baseUrl: string, pathPrefix: string, path: string): URL {
  const endpoint = new URL(baseUrl);
  const basePath = endpoint.pathname === "/" ? "" : endpoint.pathname;
  const normalizedPath = String(path || "").replace(/^\/+|\/+$/g, "");
  const normalizedPrefix = String(pathPrefix || "").replace(/^\/+|\/+$/g, "");
  const normalizedBasePath = String(basePath || "").replace(/^\/+|\/+$/g, "");

  const segments = [normalizedBasePath, normalizedPrefix, normalizedPath].filter(Boolean);
  endpoint.pathname = `/${segments.join("/")}`;
  return endpoint;
}

export async function supabaseRestRequest(
  path: string,
  options: SupabaseRestRequestOptions = {}
): Promise<any> {
  const { baseUrl, pathPrefix, defaultHeaders } = getRestConfig();
  const endpoint = buildEndpoint(baseUrl, pathPrefix, path);

  for (const [key, value] of Object.entries(options.params || {})) {
    endpoint.searchParams.set(key, value);
  }

  const headers: Record<string, string> = {
    ...defaultHeaders,
    ...(options.extraHeaders || {}),
  };

  let body: string | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const res = await fetch(endpoint.toString(), {
    method: options.method || "GET",
    headers,
    body,
    cache: "no-store",
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`REST request failed (${res.status}): ${errBody}`);
  }

  const text = await res.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function supabaseRestGet(
  path: string,
  params: Record<string, string>
): Promise<any> {
  return supabaseRestRequest(path, { method: "GET", params });
}
