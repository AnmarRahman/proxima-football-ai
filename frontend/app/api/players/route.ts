import { getDatabaseProvider } from "@/lib/database-provider";
import { hasSupabaseServerConfig, supabaseRestGet } from "@/lib/supabase-rest";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const FALLBACK_PLAYERS = [
  { id: "mbappe", name: "Kylian Mbappe" },
  { id: "haaland", name: "Erling Haaland" },
  { id: "messi", name: "Lionel Messi" },
  { id: "ronaldo", name: "Cristiano Ronaldo" },
  { id: "neymar", name: "Neymar Jr." },
];

export async function GET() {
  const provider = getDatabaseProvider();

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
        error: error?.message || "Failed to query database",
      },
      { status: 200 }
    );
  }
}



