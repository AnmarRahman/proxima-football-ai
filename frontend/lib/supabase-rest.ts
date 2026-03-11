const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

export function hasSupabaseServerConfig(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY);
}

export function getSupabaseServerConfig(): { url: string; serviceRoleKey: string } {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("Missing Supabase server configuration.");
  }
  return { url: SUPABASE_URL, serviceRoleKey: SUPABASE_SERVICE_ROLE_KEY };
}

export async function supabaseRestGet(
  path: string,
  params: Record<string, string>
): Promise<any> {
  const { url, serviceRoleKey } = getSupabaseServerConfig();
  const endpoint = new URL(`/rest/v1/${path}`, url);

  for (const [key, value] of Object.entries(params)) {
    endpoint.searchParams.set(key, value);
  }

  const res = await fetch(endpoint.toString(), {
    headers: {
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Supabase REST request failed (${res.status}): ${body}`);
  }

  return res.json();
}
