"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, CalendarRange, Target } from "lucide-react";
import { formatPosition } from "@/lib/player-position";
import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Interval = { lower: number; upper: number; method?: string | null } | null;

type ForecastPayload = {
  player: {
    id: string;
    name: string;
    nationality?: string | null;
    primary_position?: string | null;
  };
  historical_seasons?: Array<{
    season: string;
    season_start_year: number;
    season_end_year: number;
    appearances: number;
    goals: number;
    is_partial: boolean;
    model_eligible: boolean;
  }>;
  prediction: {
    scope: string;
    point: string;
    based_on_season?: string | null;
    predicted_season?: string | null;
    appearances: {
      expected: number;
      interval: Interval;
      interval_unavailable_reason?: string | null;
    };
    goals: { expected: number; interval: Interval };
    limitations: string[];
    coverage_metadata?: { eligible_seasons_used?: number; stat_scope?: string };
  };
  meta: { model_version: string; predicted_at?: string | null };
};

function ForecastCard({
  title,
  expected,
  icon,
}: {
  title: string;
  expected: number;
  icon: ReactNode;
}) {
  return (
    <Card className="overflow-hidden border-border/60 bg-card/80">
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardDescription>{title}</CardDescription>
          <CardTitle className="mt-2 text-5xl text-primary">{expected}</CardTitle>
        </div>
        <div className="rounded-full border border-primary/25 bg-primary/10 p-3 text-primary">{icon}</div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">Predicted total for the next domestic-league season</p>
      </CardContent>
    </Card>
  );
}
export function CareerPredictionDashboard(props: ForecastPayload) {
  const { player, prediction, historical_seasons = [] } = props;
  const progressionData = [
    ...historical_seasons.map((season) => ({
      season: `${season.season}${season.is_partial ? " (to date)" : ""}`,
      appearances: season.appearances,
      goals: season.goals,
      kind: season.is_partial ? "partial" : "historical",
    })),
    {
      season: `${prediction.predicted_season || "Next season"} (forecast)`,
      appearances: prediction.appearances.expected,
      goals: prediction.goals.expected,
      kind: "forecast",
    },
  ];
  const chartWidth = Math.max(760, progressionData.length * 76);

  return (
    <section className="mt-10 space-y-6 animate-fade-in">
      <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-[#17130a] via-card to-card p-6 md:p-8">
        <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-primary/10 blur-3xl" />
        <p className="relative text-xs font-semibold uppercase tracking-[0.24em] text-primary">Tier A / Next domestic-league season</p>
        <div className="relative mt-3 flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <h2 className="text-3xl font-bold text-foreground md:text-4xl">{player.name}</h2>
            <p className="mt-2 text-muted-foreground">
              {player.primary_position ? formatPosition(player.primary_position) : "Outfield Player"}{player.nationality ? ` / ${player.nationality}` : ""}
            </p>
          </div>
          <div className="rounded-xl border border-border/60 bg-black/25 px-4 py-3 text-sm">
            <p className="text-muted-foreground">Forecast season</p>
            <p className="mt-1 text-xl font-bold text-foreground">{prediction.predicted_season || "Next season"}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <ForecastCard title="Expected league appearances" expected={prediction.appearances.expected} icon={<Activity className="h-5 w-5" />} />
        <ForecastCard title="Expected league goals" expected={prediction.goals.expected} icon={<Target className="h-5 w-5" />} />
      </div>

      <Card className="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle>Career Progression</CardTitle>
          <CardDescription>
            Sourced domestic-league seasons are shown chronologically. Gold marks the next-season forecast.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm bg-slate-500" />Recorded appearances</span>
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm bg-emerald-400" />Recorded goals</span>
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm bg-primary" />Forecast</span>
          </div>

          <div>
            <p className="mb-3 text-sm font-semibold text-foreground">League appearances by season</p>
            <div className="overflow-x-auto pb-2">
              <div style={{ height: 270, width: chartWidth }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={progressionData} margin={{ top: 8, right: 12, left: 0, bottom: 48 }}>
                    <CartesianGrid vertical={false} stroke="#ffffff18" strokeDasharray="3 3" />
                    <XAxis dataKey="season" angle={-35} textAnchor="end" interval={0} height={70} tickLine={false} stroke="#a1a1aa" fontSize={11} />
                    <YAxis allowDecimals={false} tickLine={false} stroke="#a1a1aa" />
                    <Tooltip cursor={{ fill: "#ffffff08" }} contentStyle={{ background: "#090909", border: "1px solid #333", borderRadius: 8 }} />
                    <Bar dataKey="appearances" name="Appearances" radius={[5, 5, 0, 0]} maxBarSize={42}>
                      {progressionData.map((entry, index) => (
                        <Cell key={`${entry.season}-appearances-${index}`} fill={entry.kind === "forecast" ? "#d4af37" : entry.kind === "partial" ? "#94a3b8" : "#64748b"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div>
            <p className="mb-3 text-sm font-semibold text-foreground">League goals by season</p>
            <div className="overflow-x-auto pb-2">
              <div style={{ height: 270, width: chartWidth }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={progressionData} margin={{ top: 8, right: 12, left: 0, bottom: 48 }}>
                    <CartesianGrid vertical={false} stroke="#ffffff18" strokeDasharray="3 3" />
                    <XAxis dataKey="season" angle={-35} textAnchor="end" interval={0} height={70} tickLine={false} stroke="#a1a1aa" fontSize={11} />
                    <YAxis allowDecimals={false} tickLine={false} stroke="#a1a1aa" />
                    <Tooltip cursor={{ fill: "#ffffff08" }} contentStyle={{ background: "#090909", border: "1px solid #333", borderRadius: 8 }} />
                    <Bar dataKey="goals" name="Goals" radius={[5, 5, 0, 0]} maxBarSize={42}>
                      {progressionData.map((entry, index) => (
                        <Cell key={`${entry.season}-goals-${index}`} fill={entry.kind === "forecast" ? "#d4af37" : entry.kind === "partial" ? "#6ee7c8" : "#24c7a5"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-5">
        <Card className="border-border/60 bg-card/80">
          <CardHeader>
            <CardTitle>Career Data Used</CardTitle>
            <CardDescription>The historical record considered for this forecast.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex gap-3"><CalendarRange className="mt-0.5 h-4 w-4 text-primary" /><div><p className="font-medium">Based on performances through {prediction.based_on_season || "the latest completed season"}</p><p className="text-muted-foreground">{prediction.coverage_metadata?.eligible_seasons_used || historical_seasons.length} career seasons analyzed</p></div></div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-amber-500/20 bg-amber-500/[0.04]">
        <CardHeader>
          <CardTitle className="text-lg">What This Forecast Does Not Claim</CardTitle>
          <CardDescription>The validated model is intentionally limited to one domestic-league season.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
            {(prediction.limitations || []).map((limitation) => (
              <li key={limitation} className="rounded-lg border border-border/50 bg-black/15 px-3 py-2">{limitation}</li>
            ))}
            <li className="rounded-lg border border-border/50 bg-black/15 px-3 py-2">No retirement-age or full-career trajectory prediction</li>
            <li className="rounded-lg border border-border/50 bg-black/15 px-3 py-2">No assists, ratings, transfers, trophies, or goalkeeper outputs</li>
          </ul>
          {!prediction.appearances.interval && prediction.appearances.interval_unavailable_reason ? (
            <p className="mt-4 text-xs text-amber-300">Appearance interval withheld: {prediction.appearances.interval_unavailable_reason}</p>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
