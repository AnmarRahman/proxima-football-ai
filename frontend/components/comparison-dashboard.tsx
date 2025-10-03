"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Activity, Award, Crown, Target, TrendingUp, Trophy } from "lucide-react"
import { useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts"

const player1Data = {
  name: "Kylian Mbappé",
  team: "Paris Saint-Germain",
  position: "Forward",
  age: 25,
  rating: 95,
  stats: {
    goals: 44,
    assists: 10,
    appearances: 43,
    minutes: 3654,
    yellowCards: 4,
    redCards: 0,
  },
  attributes: {
    pace: 95,
    shooting: 92,
    passing: 85,
    dribbling: 94,
    defending: 35,
    physical: 88,
  },
}

const player2Data = {
  name: "Erling Haaland",
  team: "Manchester City",
  position: "Forward",
  age: 24,
  rating: 94,
  stats: {
    goals: 52,
    assists: 9,
    appearances: 45,
    minutes: 3892,
    yellowCards: 2,
    redCards: 0,
  },
  attributes: {
    pace: 89,
    shooting: 96,
    passing: 78,
    dribbling: 85,
    defending: 42,
    physical: 95,
  },
}

const attributeComparison = [
  { attribute: "Pace", player1: 95, player2: 89 },
  { attribute: "Shooting", player1: 92, player2: 96 },
  { attribute: "Passing", player1: 85, player2: 78 },
  { attribute: "Dribbling", player1: 94, player2: 85 },
  { attribute: "Defending", player1: 35, player2: 42 },
  { attribute: "Physical", player1: 88, player2: 95 },
]

const seasonComparison = [
  { season: "2021/22", player1: 39, player2: 22 },
  { season: "2022/23", player1: 41, player2: 52 },
  { season: "2023/24", player1: 44, player2: 38 },
  { season: "2024/25", player1: 12, player2: 15 },
]

const performanceMetrics = [
  { metric: "Goals per Game", player1: 1.02, player2: 1.16 },
  { metric: "Shots per Game", player1: 4.2, player2: 3.8 },
  { metric: "Pass Accuracy", player1: 83, player2: 78 },
  { metric: "Dribbles per Game", player1: 3.1, player2: 1.4 },
  { metric: "Aerial Duels Won", player1: 42, player2: 68 },
]

// Legend component for all charts
const ChartLegend = () => (
  <div className="flex items-center space-x-4 mb-2">
    <div className="flex items-center space-x-1">
      <span className="w-4 h-4 bg-yellow-400 rounded-sm block" />
      <span className="text-xs text-muted-foreground">Mbappé</span>
    </div>
    <div className="flex items-center space-x-1">
      <span className="w-4 h-4 rounded-sm block" style={{ backgroundColor: "#10b981" }} />
      <span className="text-xs text-muted-foreground">Haaland</span>
    </div>
  </div>
)

export function ComparisonDashboard() {
  const [showPlayer1, setShowPlayer1] = useState(true)
  const [showPlayer2, setShowPlayer2] = useState(true)

  return (
    <div className="space-y-8">
      {/* Player Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="border-primary/30 bg-card/90">
          <CardContent className="p-6 text-center">
            <img
              src="/football-player-portrait.png"
              alt={player1Data.name}
              className="w-24 h-24 rounded-full object-cover border-3 border-primary mx-auto mb-4"
            />
            <h3 className="text-xl font-bold text-foreground">{player1Data.name}</h3>
            <p className="text-muted-foreground">{player1Data.team}</p>
            <div className="flex items-center justify-center space-x-4 mt-3">
              <Badge className="bg-primary text-primary-foreground">{player1Data.position}</Badge>
              <span className="text-sm text-muted-foreground">Age: {player1Data.age}</span>
            </div>
            <div className="text-3xl font-bold text-primary mt-4">{player1Data.rating}</div>
            <div className="text-sm text-muted-foreground">Overall Rating</div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardContent className="p-6">
            <div className="text-center space-y-6">
              <div className="text-2xl font-bold text-primary">Head to Head</div>

              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Better Rating</span>
                  <Badge className="bg-primary text-primary-foreground">Mbappé</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">More Goals</span>
                  <Badge className="bg-chart-2 text-primary-foreground">Haaland</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Better Pace</span>
                  <Badge className="bg-primary text-primary-foreground">Mbappé</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">More Physical</span>
                  <Badge className="bg-chart-2 text-primary-foreground">Haaland</Badge>
                </div>
              </div>

              <div className="pt-4 border-t border-border">
                <div className="text-lg font-semibold text-foreground">AI Verdict</div>
                <p className="text-sm text-muted-foreground mt-2">
                  Both exceptional strikers with different strengths. Mbappé offers more versatility and pace, while
                  Haaland provides superior finishing and physicality.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-chart-2/30 bg-card/90">
          <CardContent className="p-6 text-center">
            <img
              src="/football-player-portrait.png"
              alt={player2Data.name}
              className="w-24 h-24 rounded-full object-cover border-3 border-chart-2 mx-auto mb-4"
            />
            <h3 className="text-xl font-bold text-foreground">{player2Data.name}</h3>
            <p className="text-muted-foreground">{player2Data.team}</p>
            <div className="flex items-center justify-center space-x-4 mt-3">
              <Badge className="bg-chart-2 text-primary-foreground">{player2Data.position}</Badge>
              <span className="text-sm text-muted-foreground">Age: {player2Data.age}</span>
            </div>
            <div className="text-3xl font-bold text-chart-2 mt-4">{player2Data.rating}</div>
            <div className="text-sm text-muted-foreground">Overall Rating</div>
          </CardContent>
        </Card>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {[
          { icon: Target, label: "Goals", player1: player1Data.stats.goals, player2: player2Data.stats.goals },
          { icon: Activity, label: "Assists", player1: player1Data.stats.assists, player2: player2Data.stats.assists },
          { icon: Trophy, label: "Apps", player1: player1Data.stats.appearances, player2: player2Data.stats.appearances },
          {
            icon: TrendingUp,
            label: "Goals/Game",
            player1: (player1Data.stats.goals / player1Data.stats.appearances).toFixed(2),
            player2: (player2Data.stats.goals / player2Data.stats.appearances).toFixed(2),
          },
          { icon: Award, label: "Yellow Cards", player1: player1Data.stats.yellowCards, player2: player2Data.stats.yellowCards },
          {
            icon: Crown,
            label: "Mins/Game",
            player1: Math.round(player1Data.stats.minutes / player1Data.stats.appearances),
            player2: Math.round(player2Data.stats.minutes / player2Data.stats.appearances),
          },
        ].map((stat) => (
          <Card key={stat.label} className="border-border/50 bg-card/80">
            <CardContent className="p-4 text-center">
              <stat.icon className="h-6 w-6 text-primary mx-auto mb-2" />
              <div className="space-y-1">
                <div className="text-2xl font-bold text-primary">{stat.player1}</div>
                <div className="text-2xl font-bold text-chart-2">{stat.player2}</div>
              </div>
              <div className="text-xs text-muted-foreground">{stat.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="attributes" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 bg-secondary/20">
          <TabsTrigger value="attributes">Attributes</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="seasons">Season Trends</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
        </TabsList>

        {/* Attributes */}
        <TabsContent value="attributes" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Attribute Radar</CardTitle>
                <CardDescription>FIFA-style attribute comparison</CardDescription>
                <div className="flex gap-2 mt-4">
                  <Button
                    variant={showPlayer1 ? undefined : "outline"}
                    style={{
                      backgroundColor: showPlayer1 ? "#fbbf24" : undefined,
                      color: showPlayer1 ? "#000000" : "#ffffff", // black when checked, white when unchecked
                    }}
                    size="sm"
                    onClick={() => setShowPlayer1(!showPlayer1)}
                    className="text-xs"
                  >
                    {player1Data.name}
                  </Button>
                  <Button
                    variant={showPlayer2 ? undefined : "outline"}
                    style={{
                      backgroundColor: showPlayer2 ? "#10b981" : undefined,
                      color: showPlayer2 ? "#000000" : "#ffffff", // black when checked, white when unchecked
                    }}
                    size="sm"
                    onClick={() => setShowPlayer2(!showPlayer2)}
                    className="text-xs"
                  >
                    {player2Data.name}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={attributeComparison}>
                    <PolarGrid stroke="hsl(var(--border))" />
                    <PolarAngleAxis dataKey="attribute" tick={{ fill: "#ffffff", fontSize: 12 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "#ffffff", fontSize: 10 }} />
                    {showPlayer1 && (
                      <Radar
                        name={player1Data.name}
                        dataKey="player1"
                        stroke="#fbbf24"
                        fill="#fbbf24"
                        fillOpacity={0.3}
                        strokeWidth={2}
                      />
                    )}
                    {showPlayer2 && (
                      <Radar
                        name={player2Data.name}
                        dataKey="player2"
                        stroke="#10b981"
                        fill="#10b981"
                        fillOpacity={0.2}
                        strokeWidth={2}
                        strokeDasharray="5 5"
                      />
                    )}
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Attribute Breakdown */}
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Attribute Breakdown</CardTitle>
                <CardDescription>Side-by-side attribute comparison</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {attributeComparison.map((attr) => (
                  <div key={attr.attribute} className="space-y-2">
                    <div className="flex justify-between text-sm font-medium">
                      <span>{attr.attribute}</span>
                      <div className="flex space-x-4">
                        <span className="text-primary">{attr.player1}</span>
                        <span className="text-chart-2">{attr.player2}</span>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <div className="flex-1">
                        <Progress value={attr.player1} className="h-2" />
                      </div>
                      <div className="flex-1">
                        <Progress value={attr.player2} className="h-2 [&>div]:bg-chart-2" />
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Performance */}
        <TabsContent value="performance" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>Performance Metrics</CardTitle>
              <CardDescription>Key performance indicators comparison</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartLegend />
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={performanceMetrics}
                  layout="vertical"
                  margin={{ top: 20, right: 30, left: 100, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis type="number" stroke="hsl(var(--muted-foreground))" tick={{ fill: "#ffffff", fontSize: 12 }} />
                  <YAxis
                    type="category"
                    dataKey="metric"
                    width={120}
                    stroke="hsl(var(--muted-foreground))"
                    tick={{ fill: "#ffffff", fontSize: 12 }}
                  />

                  <Bar dataKey="player1" fill="#fbbf24" name={player1Data.name} barSize={20} radius={[4, 4, 4, 4]}>
                    <LabelList dataKey="player1" position="right" fill="#ffffff" fontSize={12} />
                  </Bar>
                  <Bar dataKey="player2" fill="#10b981" name={player2Data.name} barSize={20} radius={[4, 4, 4, 4]}>
                    <LabelList dataKey="player2" position="right" fill="#ffffff" fontSize={12} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Seasons */}
        <TabsContent value="seasons" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>Season Goal Trends</CardTitle>
              <CardDescription>Goals scored per season comparison</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartLegend />
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={seasonComparison}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="season"
                    stroke="#ffffff"
                    tick={{ fill: "#ffffff", fontSize: 12 }}
                  />
                  <YAxis
                    stroke="#ffffff"
                    tick={{ fill: "#ffffff", fontSize: 12 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="player1"
                    stroke="#fbbf24"
                    strokeWidth={3}
                    name={player1Data.name}
                    dot={{ fill: "#fbbf24", strokeWidth: 2, r: 4 }}
                    label={{ position: "top", fill: "#ffffff", fontSize: 12, dy: -6, formatter: (value) => value }}
                  />
                  <Line
                    type="monotone"
                    dataKey="player2"
                    stroke="#10b981"
                    strokeWidth={3}
                    name={player2Data.name}
                    dot={{ fill: "#10b981", strokeWidth: 2, r: 4 }}
                    strokeDasharray="5 5"
                    label={{ position: "top", fill: "#ffffff", fontSize: 12, dy: -6, formatter: (value) => value }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analysis */}
        <TabsContent value="analysis" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>AI Comparison Analysis</CardTitle>
              <CardDescription>Detailed breakdown of player strengths and weaknesses</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-primary">{player1Data.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    Strong pace, dribbling, and versatility. Less physical than Haaland but highly agile and quick.
                  </p>
                </div>
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-chart-2">{player2Data.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    Exceptional finisher, strong in the air and physically dominant. Less agile but more powerful.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
