"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Player } from "@/types/player";
import { Activity, Award, Calendar, Target, TrendingUp, Trophy } from "lucide-react";
import { useState } from "react";
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

interface CareerPredictionDashboardProps {
  player: Player;
}

export function CareerPredictionDashboard({ player }: CareerPredictionDashboardProps) {
  const [showCurrentRadar, setShowCurrentRadar] = useState(true);
  const [showPeakRadar, setShowPeakRadar] = useState(true);

  // Placeholder data
  const careerData = [
    { age: 21, goals: 12, assists: 8, rating: 87 },
    { age: 22, goals: 18, assists: 12, rating: 89 },
    { age: 23, goals: 25, assists: 15, rating: 91 },
    { age: 24, goals: 32, assists: 18, rating: 93 },
    { age: 25, goals: 38, assists: 22, rating: 95 },
  ];

  const attributeData = [
    { attribute: "Pace", current: 95, predicted: 88 },
    { attribute: "Shooting", current: 92, predicted: 96 },
    { attribute: "Passing", current: 85, predicted: 90 },
    { attribute: "Dribbling", current: 94, predicted: 92 },
    { attribute: "Defending", current: 35, predicted: 40 },
    { attribute: "Physical", current: 88, predicted: 85 },
  ];

  const trophyPredictions = [
    { trophy: "Ballon d'Or", probability: 85, years: "2025, 2027" },
    { trophy: "Champions League", probability: 75, years: "2025, 2026, 2028" },
    { trophy: "World Cup", probability: 60, years: "2026" },
    { trophy: "Golden Boot", probability: 90, years: "2024, 2025, 2026" },
  ];

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Peak Age</CardTitle>
            <Calendar className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">27</div>
            <p className="text-xs text-muted-foreground">Expected peak performance</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Career Goals</CardTitle>
            <Target className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">420+</div>
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
            <CardTitle className="text-sm font-medium">Trophy Count</CardTitle>
            <Trophy className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">25+</div>
            <p className="text-xs text-muted-foreground">Major trophies predicted</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="timeline" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 bg-secondary/20">
          <TabsTrigger value="timeline">Career Timeline</TabsTrigger>
          <TabsTrigger value="attributes">Attributes</TabsTrigger>
          <TabsTrigger value="trophies">Trophy Predictions</TabsTrigger>
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
                      backgroundColor: "rgba(0, 0, 0, 0.7)", // semi-transparent dark background
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      color: "#ffffff", // text color
                      padding: "8px 12px",
                    }}
                    labelStyle={{ color: "#ffffff", fontWeight: 600 }}
                    itemStyle={{ color: "#ffffff" }}
                  />


                  <Line
                    type="monotone"
                    dataKey="goals"
                    stroke="#fbbf24" // gold
                    strokeWidth={3}
                    dot={{ fill: "#fbbf24", stroke: "#ffffff", strokeWidth: 2, r: 4 }}
                    connectNulls={true}
                    name="Goals"
                  />

                  <Line
                    type="monotone"
                    dataKey="assists"
                    stroke="#10b981" // green
                    strokeWidth={3}
                    dot={{ fill: "#10b981", stroke: "#ffffff", strokeWidth: 2, r: 4 }}
                    connectNulls={true}
                    name="Assists"
                  />

                  <Line
                    type="monotone"
                    dataKey="rating"
                    stroke="#3b82f6" // blue
                    strokeWidth={3}
                    dot={{ fill: "#3b82f6", stroke: "#ffffff", strokeWidth: 2, r: 4 }}
                    connectNulls={true}
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

        <TabsContent value="trophies" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Award className="h-5 w-5 text-primary" />
                <span>Trophy Predictions</span>
              </CardTitle>
              <CardDescription>Likelihood of winning major trophies and awards</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {trophyPredictions.map((trophy, index) => (
                <div key={index} className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg">
                  <div className="flex-1">
                    <h3 className="font-semibold text-foreground">{trophy.trophy}</h3>
                    <p className="text-sm text-muted-foreground">Predicted years: {trophy.years}</p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <div className="text-2xl font-bold text-primary">{trophy.probability}%</div>
                      <div className="text-xs text-muted-foreground">Probability</div>
                    </div>
                    <Progress value={trophy.probability} className="w-24" />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>AI Analysis Report</CardTitle>
              <CardDescription>Comprehensive career prediction analysis</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
                  <h3 className="font-semibold text-primary mb-2">Peak Performance Window</h3>
                  <p className="text-sm text-foreground">
                    Based on current trajectory and historical data, Mbappé is predicted to reach his peak between ages
                    26-28, with optimal performance at 27. His pace will naturally decline, but improved decision-making
                    and positioning will maintain elite goal-scoring output.
                  </p>
                </div>

                <div className="p-4 bg-secondary/20 rounded-lg">
                  <h3 className="font-semibold text-foreground mb-2">Career Longevity Factors</h3>
                  <p className="text-sm text-muted-foreground">
                    Excellent injury record and professional lifestyle suggest a career extending to age 35. Transition
                    to a more central role around age 30 will help maintain effectiveness as pace declines.
                  </p>
                </div>

                <div className="p-4 bg-secondary/20 rounded-lg">
                  <h3 className="font-semibold text-foreground mb-2">Trophy Potential</h3>
                  <p className="text-sm text-muted-foreground">
                    High probability of multiple Ballon d'Or wins during peak years. Champions League success depends on
                    team moves and squad quality. World Cup 2026 represents best opportunity for international glory.
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

