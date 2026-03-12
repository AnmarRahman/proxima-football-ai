import { isPostgresProvider } from "@/lib/database-provider";

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

function readEnv(name: string): string {
  return String(process.env[name] || "").trim();
}

function getSupabaseUrl(): string {
  return readEnv("NEXT_PUBLIC_SUPABASE_URL") || readEnv("SUPABASE_URL");
}

function getSupabaseServiceRoleKey(): string {
  return readEnv("SUPABASE_SERVICE_ROLE_KEY");
}

function getPostgrestUrl(): string {
  return readEnv("POSTGREST_URL");
}

function getPostgrestApiKey(): string {
  return readEnv("POSTGREST_API_KEY");
}

function hasPostgresRestConfig(): boolean {
  return Boolean(getPostgrestUrl());
}

function hasSupabaseConfig(): boolean {
  return Boolean(getSupabaseUrl() && getSupabaseServiceRoleKey());
}

export function hasSupabaseServerConfig(): boolean {
  return isPostgresProvider() ? hasPostgresRestConfig() : hasSupabaseConfig();
}

export function getSupabaseServerConfig(): { url: string; serviceRoleKey: string } {
  if (isPostgresProvider()) {
    const postgrestUrl = getPostgrestUrl();
    if (!postgrestUrl) {
      throw new Error("Missing PostgREST server configuration.");
    }

    return {
      url: postgrestUrl,
      serviceRoleKey: getPostgrestApiKey(),
    };
  }

  const supabaseUrl = getSupabaseUrl();
  const serviceRoleKey = getSupabaseServiceRoleKey();

  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error("Missing Supabase server configuration.");
  }

  return { url: supabaseUrl, serviceRoleKey };
}

function getRestConfig(): RestConfig {
  if (isPostgresProvider()) {
    const postgrestUrl = getPostgrestUrl();
    if (!postgrestUrl) {
      throw new Error("Missing PostgREST server configuration. Set POSTGREST_URL.");
    }

    const headers: Record<string, string> = {};
    const postgrestApiKey = getPostgrestApiKey();
    if (postgrestApiKey) {
      headers.Authorization = `Bearer ${postgrestApiKey}`;
    }

    return {
      baseUrl: postgrestUrl,
      pathPrefix: "",
      defaultHeaders: headers,
    };
  }

  const supabaseUrl = getSupabaseUrl();
  const serviceRoleKey = getSupabaseServiceRoleKey();

  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error("Missing Supabase server configuration.");
  }

  return {
    baseUrl: supabaseUrl,
    pathPrefix: "/rest/v1",
    defaultHeaders: {
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
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
