"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, CalendarRange, Database, Target } from "lucide-react";
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

function RangeText({ interval }: { interval: Interval }) {
  if (!interval) return <span>No reliable interval available</span>;
  return <span>{interval.lower}-{interval.upper} calibrated range</span>;
}

function ForecastCard({
  title,
  expected,
  interval,
  icon,
}: {
  title: string;
  expected: number;
  interval: Interval;
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
        <p className="text-sm text-muted-foreground"><RangeText interval={interval} /></p>
        {interval ? (
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary/40 via-primary to-primary/40"
              style={{ width: `${Math.min(100, Math.max(18, ((interval.upper - interval.lower + 1) / Math.max(interval.upper, 1)) * 100))}%` }}
            />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
export function CareerPredictionDashboard(props: ForecastPayload) {
  const { player, prediction, meta } = props;
  const chartData = [
    { metric: "Appearances", expected: prediction.appearances.expected, fill: "#d4af37" },
    { metric: "Goals", expected: prediction.goals.expected, fill: "#24c7a5" },
  ];
  const predictedDate = meta.predicted_at ? new Date(meta.predicted_at).toLocaleString() : "Unknown";

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
        <ForecastCard title="Expected league appearances" expected={prediction.appearances.expected} interval={prediction.appearances.interval} icon={<Activity className="h-5 w-5" />} />
        <ForecastCard title="Expected league goals" expected={prediction.goals.expected} interval={prediction.goals.interval} icon={<Target className="h-5 w-5" />} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <Card className="border-border/60 bg-card/80">
          <CardHeader>
            <CardTitle>Next-Season Output</CardTitle>
            <CardDescription>Point forecasts only; the two metrics use different units.</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid vertical={false} stroke="#ffffff18" strokeDasharray="3 3" />
                <XAxis dataKey="metric" tickLine={false} stroke="#a1a1aa" />
                <YAxis allowDecimals={false} tickLine={false} stroke="#a1a1aa" />
                <Tooltip cursor={{ fill: "#ffffff08" }} contentStyle={{ background: "#090909", border: "1px solid #333", borderRadius: 8 }} />
                <Bar dataKey="expected" name="Expected" radius={[7, 7, 0, 0]} maxBarSize={72}>
                  {chartData.map((entry) => <Cell key={entry.metric} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/80">
          <CardHeader>
            <CardTitle>Prediction Record</CardTitle>
            <CardDescription>Traceability for this stored result.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex gap-3"><CalendarRange className="mt-0.5 h-4 w-4 text-primary" /><div><p className="font-medium">Based on {prediction.based_on_season || "latest completed season"}</p><p className="text-muted-foreground">Prediction point: {prediction.point}</p></div></div>
            <div className="flex gap-3"><Database className="mt-0.5 h-4 w-4 text-primary" /><div><p className="font-medium">Model {meta.model_version}</p><p className="text-muted-foreground">{prediction.coverage_metadata?.eligible_seasons_used || "Unknown"} eligible seasons used</p></div></div>
            <div className="rounded-lg bg-secondary/30 p-3"><p className="text-xs text-muted-foreground">Generated</p><p className="mt-1 font-medium">{predictedDate}</p></div>
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
