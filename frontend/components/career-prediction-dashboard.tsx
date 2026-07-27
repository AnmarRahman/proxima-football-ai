"use client";

import { AIAnalysisLoader } from "@/components/ai-analysis-loader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Activity, Calendar, Target, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface PlayerSeasonStats {
  season?: number;
  age?: number;
  goals?: number;
  assists?: number;
  rating?: number;
  sprint_speed_kmh?: number;
  shots_per_game?: number;
  key_passes?: number;
  successful_dribbles?: number;
  tackles_per_game?: number;
  stamina?: number | string;
}

interface Player {
  id: string;
  name: string;
  stats: PlayerSeasonStats[];
  currentStats?: PlayerSeasonStats | null;
  meta?: {
    confidence_score?: number | string | null;
    predicted_at?: string | null;
    horizon_seasons?: number | null;
  } | null;
  [key: string]: any;
}

interface CareerPredictionDashboardProps {
  player: Player;
}

type AttributeKey =
  | "sprint_speed_kmh"
  | "shots_per_game"
  | "key_passes"
  | "successful_dribbles"
  | "tackles_per_game"
  | "stamina";

const ATTRIBUTE_DEFINITIONS: Array<{
  attribute: string;
  key: AttributeKey;
  min: number;
  max: number;
  decimals: number;
  unit?: string;
}> = [
  { attribute: "Pace", key: "sprint_speed_kmh", min: 25, max: 38, decimals: 1, unit: " km/h" },
  { attribute: "Shooting", key: "shots_per_game", min: 0, max: 6, decimals: 1 },
  { attribute: "Passing", key: "key_passes", min: 0, max: 180, decimals: 0 },
  { attribute: "Dribbling", key: "successful_dribbles", min: 0, max: 250, decimals: 0 },
  { attribute: "Defending", key: "tackles_per_game", min: 0, max: 5, decimals: 1 },
  { attribute: "Physical", key: "stamina", min: 0, max: 5, decimals: 1 },
];

const STAMINA_LABELS: Record<string, number> = {
  poor: 1,
  low: 2,
  developing: 2.5,
  medium: 3,
  moderate: 3,
  normal: 3,
  good: 3.5,
  high: 4,
  "very high": 4.5,
  excellent: 5,
  elite: 5,
};

function toNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function attributeValue(season: PlayerSeasonStats | null | undefined, key: AttributeKey): number | null {
  const value = season?.[key];
  if (key === "stamina" && typeof value === "string") {
    return STAMINA_LABELS[value.trim().toLowerCase()] ?? null;
  }
  return toNumber(value);
}

function attributeScore(value: number | null, min: number, max: number): number {
  if (value === null || max <= min) {
    return 0;
  }
  return Math.round(Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100)));
}

function formatAttribute(value: number | null, decimals: number, unit = ""): string {
  return value === null ? "N/A" : `${value.toFixed(decimals)}${unit}`;
}

function performanceScore(season: PlayerSeasonStats): number {
  return (toNumber(season.rating) ?? 0) * 10
    + (toNumber(season.goals) ?? 0) * 1.25
    + (toNumber(season.assists) ?? 0);
}

export function CareerPredictionDashboard({ player }: CareerPredictionDashboardProps) {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
  }, [player.id]);

  if (isLoading) {
    return (
      <div className="mt-8">
        <AIAnalysisLoader playerName={player.name} onComplete={() => setIsLoading(false)} />
      </div>
    );
  }

  const stats: PlayerSeasonStats[] = player.stats || [];
  const rawCareerData = stats.map((season, index) => ({
    age: Math.round(toNumber(season.age) ?? 21 + index),
    goals: Math.max(0, Math.round(toNumber(season.goals) ?? 0)),
    assists: Math.max(0, Math.round(toNumber(season.assists) ?? 0)),
    rating: Math.max(0, Number((toNumber(season.rating) ?? 0).toFixed(1))),
  }));
  const chartStatMaximum = Math.max(
    10,
    ...rawCareerData.flatMap((season) => [season.goals, season.assists])
  );
  const chartStatCeiling = Math.ceil(chartStatMaximum / 10) * 10;
  const ratingBarScale = chartStatCeiling / 10;
  const careerData = rawCareerData.map((season) => ({
    ...season,
    ratingBar: season.rating * ratingBarScale,
  }));

  const firstPrediction = stats[0] || {};
  const peakSeason = stats.reduce<PlayerSeasonStats>(
    (best, season) => performanceScore(season) > performanceScore(best) ? season : best,
    firstPrediction
  );
  const currentSource = player.currentStats || firstPrediction;

  const attributeData = ATTRIBUTE_DEFINITIONS.map((definition) => {
    let currentRaw = attributeValue(currentSource, definition.key);
    const firstForecastRaw = attributeValue(firstPrediction, definition.key);

    // A zero pace/stamina value in imported data represents missing physical data.
    if ((definition.key === "sprint_speed_kmh" || definition.key === "stamina") && currentRaw === 0) {
      currentRaw = firstForecastRaw;
    }
    if (currentRaw === null) {
      currentRaw = firstForecastRaw;
    }

    const peakRaw = attributeValue(peakSeason, definition.key);
    const current = attributeScore(currentRaw, definition.min, definition.max);
    const peak = attributeScore(peakRaw, definition.min, definition.max);

    return {
      ...definition,
      current,
      peak,
      currentLabel: formatAttribute(currentRaw, definition.decimals, definition.unit),
      peakLabel: formatAttribute(peakRaw, definition.decimals, definition.unit),
      delta: peak - current,
    };
  });

  const peakAge = Math.round(toNumber(peakSeason.age) ?? toNumber(careerData[0]?.age) ?? 0);
  const forecastGoals = careerData.reduce((total, season) => total + season.goals, 0);
  const forecastEndAge = careerData.length ? careerData[careerData.length - 1].age : null;
  const rawConfidence = toNumber(player.meta?.confidence_score);
  const confidence = rawConfidence === null ? null : Math.round(Math.max(0, Math.min(1, rawConfidence)) * 100);
  const predictionDate = player.meta?.predicted_at
    ? new Date(player.meta.predicted_at).toLocaleDateString()
    : "Not available";

  return (
    <div className="mt-8 space-y-8">
      <div className="animate-fade-in space-y-4 text-center">
        <div className="inline-flex items-center space-x-2 rounded-full border border-green-500/30 bg-green-500/10 px-4 py-2">
          <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
          <span className="text-sm font-medium text-green-500">Analysis Complete</span>
        </div>
        <h2 className="text-3xl font-bold text-foreground">{player.name}&apos;s Career Prediction</h2>
        <p className="mx-auto max-w-2xl text-muted-foreground">
          The forecast uses season performance, injury, physical, tactical, age, and position data from the current model.
        </p>
      </div>

      <div className="grid animate-slide-up grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4" style={{ animationDelay: "0.2s" }}>
        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Peak Age</CardTitle>
            <Calendar className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{peakAge || "N/A"}</div>
            <p className="text-xs text-muted-foreground">Strongest projected season</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Forecast Goals</CardTitle>
            <Target className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{forecastGoals}</div>
            <p className="text-xs text-muted-foreground">Across predicted seasons only</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Forecast End</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{forecastEndAge ?? "N/A"}</div>
            <p className="text-xs text-muted-foreground">Last modeled age, not guaranteed retirement</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Confidence</CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{confidence === null ? "N/A" : `${confidence}%`}</div>
            <p className="text-xs text-muted-foreground">Model confidence estimate</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="timeline" className="animate-slide-up space-y-6" style={{ animationDelay: "0.4s" }}>
        <TabsList className="grid w-full grid-cols-3 bg-secondary/20">
          <TabsTrigger value="timeline">Career Timeline</TabsTrigger>
          <TabsTrigger value="attributes">Attributes</TabsTrigger>
          <TabsTrigger value="analysis">AI Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="timeline" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span>Career Trajectory</span>
              </CardTitle>
              <CardDescription>Grouped goals, assists, and rating bars for every predicted age</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
                <span><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm bg-[#f4b41a]" />Goals</span>
                <span><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm bg-[#24c7a5]" />Assists</span>
                <span><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm bg-[#4f8cff]" />Rating (right axis)</span>
              </div>
              <ResponsiveContainer width="100%" height={420}>
                <BarChart data={careerData} barCategoryGap="18%" margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#ffffff1f" />
                  <XAxis dataKey="age" stroke="#a1a1aa" tick={{ fill: "#d4d4d8", fontSize: 12 }} tickLine={false} />
                  <YAxis yAxisId="stats" domain={[0, chartStatCeiling]} allowDecimals={false} stroke="#a1a1aa" tick={{ fill: "#d4d4d8", fontSize: 12 }} tickLine={false} />
                  <YAxis yAxisId="rating" orientation="right" domain={[0, 10]} stroke="#4f8cff" tick={{ fill: "#93b4ff", fontSize: 12 }} tickLine={false} />
                  <Tooltip
                    cursor={{ fill: "#ffffff0a" }}
                    contentStyle={{
                      backgroundColor: "rgba(8, 8, 8, 0.96)",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      color: "#ffffff",
                    }}
                    labelFormatter={(age) => `Age ${age}`}
                    formatter={(value: number | string, name: string, entry: any) => [
                      name === "Rating" ? Number(entry?.payload?.rating ?? 0).toFixed(1) : value,
                      name,
                    ]}
                  />
                  <Bar yAxisId="stats" dataKey="goals" name="Goals" fill="#f4b41a" radius={[4, 4, 0, 0]} maxBarSize={24} />
                  <Bar yAxisId="stats" dataKey="assists" name="Assists" fill="#24c7a5" radius={[4, 4, 0, 0]} maxBarSize={24} />
                  <Bar yAxisId="stats" dataKey="ratingBar" name="Rating" fill="#4f8cff" radius={[4, 4, 0, 0]} maxBarSize={24} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="attributes" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>Attribute Evolution</CardTitle>
              <CardDescription>
                Latest recorded season versus the strongest projected season. Display bars are normalized to a 0-100 scale; labels show raw values.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-6 flex flex-wrap gap-4 rounded-lg border border-border/60 bg-black/20 p-3 text-xs">
                <span className="font-semibold text-sky-300"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-sky-400" />Current recorded</span>
                <span className="font-semibold text-amber-300"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-amber-400" />Predicted peak</span>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                {attributeData.map((attribute) => (
                  <div key={attribute.attribute} className="rounded-xl border border-border/60 bg-black/20 p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <span className="font-semibold text-foreground">{attribute.attribute}</span>
                      <span className={`rounded-full px-2 py-1 text-xs font-bold ${attribute.delta > 0 ? "bg-emerald-500/15 text-emerald-300" : attribute.delta < 0 ? "bg-rose-500/15 text-rose-300" : "bg-zinc-500/15 text-zinc-300"}`}>
                        {attribute.delta > 0 ? "+" : ""}{attribute.delta} pts
                      </span>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <div className="mb-1 flex justify-between text-xs"><span className="text-sky-300">Current</span><span className="font-mono text-zinc-200">{attribute.currentLabel}</span></div>
                        <div className="h-2.5 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full bg-sky-400" style={{ width: `${attribute.current}%` }} /></div>
                      </div>
                      <div>
                        <div className="mb-1 flex justify-between text-xs"><span className="text-amber-300">Peak</span><span className="font-mono text-zinc-200">{attribute.peakLabel}</span></div>
                        <div className="h-2.5 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full bg-amber-400" style={{ width: `${attribute.peak}%` }} /></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>Model Summary</CardTitle>
              <CardDescription>Traceable output from the latest stored prediction for {player.name}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border border-primary/20 bg-primary/10 p-4">
                <h3 className="mb-2 font-semibold text-primary">Projected Peak</h3>
                <p className="text-sm text-foreground">
                  The model&apos;s strongest projected season is age {peakAge || "N/A"}, based on the combined rating, goals, and assists forecast.
                </p>
              </div>
              <div className="rounded-lg bg-secondary/20 p-4">
                <h3 className="mb-2 font-semibold text-foreground">Forecast Horizon</h3>
                <p className="text-sm text-muted-foreground">
                  This run contains {careerData.length} predicted season{careerData.length === 1 ? "" : "s"} and ends at age {forecastEndAge ?? "N/A"}. The endpoint is a pipeline setting, not a claim that the player will retire at that age.
                </p>
              </div>
              <div className="rounded-lg bg-secondary/20 p-4">
                <h3 className="mb-2 font-semibold text-foreground">Scope</h3>
                <p className="text-sm text-muted-foreground">
                  The current model predicts season statistics. It does not yet model transfers, trophies, team quality, selection decisions, or a separate probability of retirement.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-4 pt-2 md:grid-cols-3">
                <div className="rounded-lg bg-card/50 p-4 text-center"><div className="text-2xl font-bold text-primary">{confidence === null ? "N/A" : `${confidence}%`}</div><div className="text-sm text-muted-foreground">Confidence estimate</div></div>
                <div className="rounded-lg bg-card/50 p-4 text-center"><div className="text-2xl font-bold text-primary">{careerData.length}</div><div className="text-sm text-muted-foreground">Forecast seasons</div></div>
                <div className="rounded-lg bg-card/50 p-4 text-center"><div className="text-sm font-bold text-primary">{predictionDate}</div><div className="text-sm text-muted-foreground">Prediction date</div></div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
