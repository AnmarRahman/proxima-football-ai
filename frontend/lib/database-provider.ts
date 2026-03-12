export type DatabaseProvider = "supabase" | "postgres";

export function getDatabaseProvider(): DatabaseProvider {
  const value = String(process.env.DATABASE_PROVIDER || "postgres").trim().toLowerCase();
  return value === "supabase" ? "supabase" : "postgres";
}

export function isPostgresProvider(): boolean {
  return getDatabaseProvider() === "postgres";
}
