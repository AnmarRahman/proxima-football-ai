import { getDatabaseProvider, isSQLiteProvider } from "@/lib/database-provider";
import { hasSupabaseServerConfig, supabaseRestGet } from "@/lib/supabase-rest";
import { sqliteAll } from "@/lib/sqlite-db";
import { NextResponse } from "next/server";

const FALLBACK_PLAYERS = [
  { id: "mbappe", name: "Kylian Mbappe" },
  { id: "haaland", name: "Erling Haaland" },
  { id: "messi", name: "Lionel Messi" },
  { id: "ronaldo", name: "Cristiano Ronaldo" },
  { id: "neymar", name: "Neymar Jr." },
];

export async function GET() {
  const provider = getDatabaseProvider();

  if (isSQLiteProvider()) {
    try {
      const rows = sqliteAll<{ id: string; name: string }>(
        `
        select id, name
        from players
        where coalesce(is_retired, 0) = 0
          and coalesce(over_35, 0) = 0
        order by name asc
        `
      );

      const players = (rows || []).map((row) => ({
        id: String(row.id),
        name: String(row.name),
      }));

      return NextResponse.json({ players, source: "sqlite", provider });
    } catch (error: any) {
      return NextResponse.json(
        {
          players: FALLBACK_PLAYERS,
          source: "fallback",
          provider,
          error: error?.message || "Failed to query SQLite",
        },
        { status: 200 }
      );
    }
  }

  if (!hasSupabaseServerConfig()) {
    return NextResponse.json({ players: FALLBACK_PLAYERS, source: "fallback", provider });
  }

  try {
    const rows = await supabaseRestGet("players", {
      select: "id,name,is_retired,over_35",
      is_retired: "eq.false",
      over_35: "eq.false",
      order: "name.asc",
    });

    const players = (rows || []).map((row: any) => ({
      id: String(row.id),
      name: String(row.name),
    }));

    return NextResponse.json({ players, source: "database", provider });
  } catch (error: any) {
    return NextResponse.json(
      {
        players: FALLBACK_PLAYERS,
        source: "fallback",
        provider,
        error: error?.message || "Failed to query Supabase",
      },
      { status: 200 }
    );
  }
}
