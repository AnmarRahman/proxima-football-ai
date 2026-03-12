export type DatabaseProvider = "supabase" | "sqlite" | "postgres";

export function getDatabaseProvider(): DatabaseProvider {
  const value = String(process.env.DATABASE_PROVIDER || "postgres").trim().toLowerCase();
  if (value === "sqlite") {
    return "sqlite";
  }
  if (value === "postgres") {
    return "postgres";
  }
  return "supabase";
}

export function isSQLiteProvider(): boolean {
  return getDatabaseProvider() === "sqlite";
}

export function isPostgresProvider(): boolean {
  return getDatabaseProvider() === "postgres";
}
