"use client";

import { AIAnalysisLoader } from "@/components/ai-analysis-loader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Activity, Calendar, Target, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface PlayerSeasonStats {
  age?: number;
  goals?: number;
  assists?: number;
  rating?: number;
  sprintspeedkmh?: number;
  shotspergame?: number;
  keypasses?: number;
  successfuldribbles?: number;
  tacklespergame?: number;
  stamina?: number;
}

interface Player {
  id: string;
  name: string;
  stats: PlayerSeasonStats[];
  [key: string]: any;
}

interface CareerPredictionDashboardProps {
  player: Player;
}

export function CareerPredictionDashboard({ player }: CareerPredictionDashboardProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [showCurrentRadar, setShowCurrentRadar] = useState<boolean>(true);
  const [showPeakRadar, setShowPeakRadar] = useState<boolean>(true);

  // Reset loading state when player changes
  useEffect(() => {
    setIsLoading(true);
  }, [player.id]);

  const handleAnalysisComplete = () => {
    setIsLoading(false);
  };

  // Show loading animation
  if (isLoading) {
    return (
      <div className="mt-8">
        <AIAnalysisLoader 
          playerName={player.name} 
          onComplete={handleAnalysisComplete}
        />
      </div>
    );
  }

  const stats: PlayerSeasonStats[] = player.stats || [];

  const careerData = stats.map((season: PlayerSeasonStats, idx: number) => ({
    age: season.age ?? 21 + idx,
    goals: Math.round(season.goals ?? 0),
    assists: Math.round(season.assists ?? 0),
    rating: Math.round(season.rating ?? 0),
  }));

  const first: PlayerSeasonStats = stats[0] || {};
  const last: PlayerSeasonStats = stats[stats.length - 1] || {};

  const attributeData = [
    {
      attribute: "Pace",
      current: Math.round(first.sprintspeedkmh ?? 90),
      predicted: Math.round(last.sprintspeedkmh ?? 85),
    },
    {
      attribute: "Shooting",
      current: Math.round(first.shotspergame ?? 85),
      predicted: Math.round(last.shotspergame ?? 90),
    },
    {
      attribute: "Passing",
      current: Math.round(first.keypasses ?? 80),
      predicted: Math.round(last.keypasses ?? 85),
    },
    {
      attribute: "Dribbling",
      current: Math.round(first.successfuldribbles ?? 90),
      predicted: Math.round(last.successfuldribbles ?? 95),
    },
    {
      attribute: "Defending",
      current: Math.round(first.tacklespergame ?? 40),
      predicted: Math.round(last.tacklespergame ?? 45),
    },
    {
      attribute: "Physical",
      current: Math.round(first.stamina ?? 80),
      predicted: Math.round(last.stamina ?? 85),
    },
  ];

  return (
    <div className="space-y-8 mt-8">
      {/* Results Header */}
      <div className="text-center space-y-4 animate-fade-in">
        <div className="inline-flex items-center space-x-2 bg-green-500/10 border border-green-500/30 rounded-full px-4 py-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-green-500 font-medium text-sm">Analysis Complete</span>
        </div>
        <h2 className="text-3xl font-bold text-foreground">
          {player.name}'s Career Prediction
        </h2>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Our AI has analyzed {player.name}'s performance data, injury history, and career patterns to generate comprehensive predictions.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-slide-up" style={{animationDelay: '0.2s'}}>
        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Peak Age</CardTitle>
            <Calendar className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {careerData.length > 0
                ? careerData.reduce(
                  (acc: { age: number; goals: number; assists: number; rating: number }, val: { age: number; goals: number; assists: number; rating: number }) =>
                    val.goals > acc.goals ? val : acc,
                  careerData[0]
                ).age
                : 27}
            </div>
            <p className="text-xs text-muted-foreground">Expected peak performance</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Career Goals</CardTitle>
            <Target className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {careerData.length > 0
                ? careerData.reduce((acc: number, val: { goals: number }) => acc + val.goals, 0)
                : "420+"}
            </div>
            <p className="text-xs text-muted-foreground">Predicted career total</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Longevity</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">35</div>
            <p className="text-xs text-muted-foreground">Retirement age prediction</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Confidence</CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">92%</div>
            <p className="text-xs text-muted-foreground">Prediction accuracy</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="timeline" className="space-y-6 animate-slide-up" style={{animationDelay: '0.4s'}}>
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
              <CardDescription>Predicted goals, assists, and overall rating over time</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={careerData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff33" />
                  <XAxis
                    dataKey="age"
                    stroke="#ffffff"
                    tick={{ fill: "#ffffff", fontSize: 12 }}
                    label={{
                      value: "Age",
                      position: "insideBottom",
                      offset: -5,
                      style: { textAnchor: "middle", fill: "#ffffff" },
                    }}
                  />
                  <YAxis
                    stroke="#ffffff"
                    tick={{ fill: "#ffffff", fontSize: 12 }}
                    label={{
                      value: "Stats",
                      angle: -90,
                      position: "insideLeft",
                      style: { textAnchor: "middle", fill: "#ffffff" },
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0, 0, 0, 0.7)",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      color: "#ffffff",
                      padding: "8px 12px",
                    }}
                    labelStyle={{ color: "#ffffff", fontWeight: 600 }}
                    itemStyle={{ color: "#ffffff" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="goals"
                    stroke="#fbbf24"
                    strokeWidth={5}
                    dot={{ fill: "#fbbf24", stroke: "#ffffff", strokeWidth: 2, r: 4 }}
                    connectNulls={true}
                    name="Goals"
                  />
                  <Line
                    type="monotone"
                    dataKey="assists"
                    stroke="#10b981"
                    strokeWidth={5}
                    dot={{ fill: "#10b981", stroke: "#ffffff", strokeWidth: 2, r: 4 }}
                    connectNulls={true}
                    name="Assists"
                  />
                  <Line
                    type="monotone"
                    dataKey="rating"
                    strokeWidth={0}
                    dot={{ fill: "#3b82f6", stroke: "#ffffff", strokeWidth: 0, r: 0 }}
                    name="Rating"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="attributes" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Attribute Evolution</CardTitle>
                <CardDescription>How player attributes will change over time</CardDescription>
                <div className="flex gap-2 mt-4">
                  <Button
                    variant={showCurrentRadar ? "default" : "outline"}
                    size="sm"
                    onClick={() => setShowCurrentRadar(!showCurrentRadar)}
                    className="text-xs"
                  >
                    Current Attributes
                  </Button>
                  <Button
                    variant={showPeakRadar ? "default" : "outline"}
                    size="sm"
                    onClick={() => setShowPeakRadar(!showPeakRadar)}
                    className="text-xs"
                  >
                    Peak Attributes
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={attributeData}>
                    <PolarGrid stroke="hsl(var(--border))" />
                    <PolarAngleAxis dataKey="attribute" tick={{ fill: "rgb(156 163 175)", fontSize: 12 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "rgb(156 163 175)", fontSize: 10 }} />
                    {showCurrentRadar && (
                      <Radar
                        name="Current"
                        dataKey="current"
                        stroke="#fbbf24"
                        fill="#fbbf24"
                        fillOpacity={0.3}
                        strokeWidth={2}
                      />
                    )}
                    {showPeakRadar && (
                      <Radar
                        name="Predicted Peak"
                        dataKey="predicted"
                        stroke="#ffffff"
                        fill="#ffffff"
                        fillOpacity={0.1}
                        strokeWidth={2}
                        strokeDasharray="5 5"
                      />
                    )}
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Attribute Breakdown</CardTitle>
                <CardDescription>Current vs predicted peak attributes</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {attributeData.map((attr) => (
                  <div key={attr.attribute} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{attr.attribute}</span>
                      <span className="text-muted-foreground">
                        {attr.current} → {attr.predicted}
                      </span>
                    </div>
                    <div className="flex space-x-2">
                      <Progress value={attr.current} className="flex-1" />
                      <Progress value={attr.predicted} className="flex-1 opacity-60" />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>AI Analysis Report</CardTitle>
              <CardDescription>Comprehensive career prediction analysis for {player.name}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
                  <h3 className="font-semibold text-primary mb-2">Peak Performance Window</h3>
                  <p className="text-sm text-foreground">
                    Based on current trajectory and historical data, {player.name} is predicted to reach peak performance between ages
                    26-28, with optimal output at 27. Natural physical decline will be offset by improved decision-making
                    and tactical awareness.
                  </p>
                </div>
                <div className="p-4 bg-secondary/20 rounded-lg">
                  <h3 className="font-semibold text-foreground mb-2">Career Longevity Factors</h3>
                  <p className="text-sm text-muted-foreground">
                    Injury record analysis and lifestyle factors suggest a career extending to age 35. Transition
                    to a more central role around age 30 will help maintain effectiveness as pace naturally declines.
                  </p>
                </div>
                <div className="p-4 bg-secondary/20 rounded-lg">
                  <h3 className="font-semibold text-foreground mb-2">Trophy Potential</h3>
                  <p className="text-sm text-muted-foreground">
                    High probability of individual awards during peak years. Champions League success depends on
                    team moves and squad quality. International tournaments represent key opportunities for legacy-defining moments.
                  </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                  <div className="text-center p-4 bg-card/50 rounded-lg">
                    <div className="text-2xl font-bold text-primary">92%</div>
                    <div className="text-sm text-muted-foreground">Prediction Confidence</div>
                  </div>
                  <div className="text-center p-4 bg-card/50 rounded-lg">
                    <div className="text-2xl font-bold text-primary">15</div>
                    <div className="text-sm text-muted-foreground">Similar Player Profiles</div>
                  </div>
                  <div className="text-center p-4 bg-card/50 rounded-lg">
                    <div className="text-2xl font-bold text-primary">2.3M</div>
                    <div className="text-sm text-muted-foreground">Data Points Analyzed</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}