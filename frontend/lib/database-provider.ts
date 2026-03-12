export type DatabaseProvider = "supabase" | "sqlite";

export function getDatabaseProvider(): DatabaseProvider {
  const value = String(process.env.DATABASE_PROVIDER || "supabase").trim().toLowerCase();
  return value === "sqlite" ? "sqlite" : "supabase";
}

export function isSQLiteProvider(): boolean {
  return getDatabaseProvider() === "sqlite";
}
