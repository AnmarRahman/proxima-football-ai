import { hasSupabaseServerConfig, supabaseRestGet } from "@/lib/supabase-rest";
import { NextResponse } from "next/server";

const FALLBACK_PLAYERS = [
  { id: "mbappe", name: "Kylian Mbappe" },
  { id: "haaland", name: "Erling Haaland" },
  { id: "messi", name: "Lionel Messi" },
  { id: "ronaldo", name: "Cristiano Ronaldo" },
  { id: "neymar", name: "Neymar Jr." },
];

export async function GET() {
  if (!hasSupabaseServerConfig()) {
    return NextResponse.json({ players: FALLBACK_PLAYERS, source: "fallback" });
  }

  try {
    const rows = await supabaseRestGet("players", {
      select: "id,name,is_retired",
      is_retired: "eq.false",
      order: "name.asc",
    });

    const players = (rows || []).map((row: any) => ({
      id: String(row.id),
      name: String(row.name),
    }));

    return NextResponse.json({ players, source: "database" });
  } catch (error: any) {
    return NextResponse.json(
      {
        players: FALLBACK_PLAYERS,
        source: "fallback",
        error: error?.message || "Failed to query Supabase",
      },
      { status: 200 }
    );
  }
}
