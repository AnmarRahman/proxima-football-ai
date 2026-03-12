const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

export type SupabaseRestRequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  params?: Record<string, string>;
  body?: unknown;
  extraHeaders?: Record<string, string>;
};

export function hasSupabaseServerConfig(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY);
}

export function getSupabaseServerConfig(): { url: string; serviceRoleKey: string } {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("Missing Supabase server configuration.");
  }
  return { url: SUPABASE_URL, serviceRoleKey: SUPABASE_SERVICE_ROLE_KEY };
}

export async function supabaseRestRequest(
  path: string,
  options: SupabaseRestRequestOptions = {}
): Promise<any> {
  const { url, serviceRoleKey } = getSupabaseServerConfig();
  const endpoint = new URL(`/rest/v1/${path}`, url);

  for (const [key, value] of Object.entries(options.params || {})) {
    endpoint.searchParams.set(key, value);
  }

  const headers: Record<string, string> = {
    apikey: serviceRoleKey,
    Authorization: `Bearer ${serviceRoleKey}`,
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
    throw new Error(`Supabase REST request failed (${res.status}): ${errBody}`);
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
