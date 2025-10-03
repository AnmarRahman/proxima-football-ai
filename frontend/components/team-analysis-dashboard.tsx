"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AlertTriangle, Calendar, Star, Target, TrendingUp, Users } from "lucide-react"
import { useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

const squadData = {
  name: "Manchester City",
  totalPlayers: 25,
  avgAge: 27.2,
  avgRating: 82.4,
  marketValue: "€1.2B",
  peakWindow: "2024-2026",
  strengths: ["Midfield Depth", "Tactical Flexibility", "Experience"],
  weaknesses: ["Aging Defense", "Striker Dependency"],
}

const ageDistribution = [
  { ageGroup: "18-21", count: 3, percentage: 12 },
  { ageGroup: "22-25", count: 8, percentage: 32 },
  { ageGroup: "26-29", count: 10, percentage: 40 },
  { ageGroup: "30-33", count: 3, percentage: 12 },
  { ageGroup: "34+", count: 1, percentage: 4 },
]

const positionBreakdown = [
  { position: "Goalkeepers", count: 3, avgAge: 28.5, avgRating: 84 },
  { position: "Defenders", count: 8, avgAge: 28.8, avgRating: 83 },
  { position: "Midfielders", count: 9, avgAge: 26.2, avgRating: 85 },
  { position: "Forwards", count: 5, avgAge: 26.8, avgRating: 87 },
]

const futureProjections = [
  { year: 2024, rating: 89, peakPlayers: 15, avgAge: 27.2 },
  { year: 2025, rating: 90, peakPlayers: 18, avgAge: 28.2 },
  { year: 2026, rating: 89, peakPlayers: 16, avgAge: 29.2 },
  { year: 2027, rating: 87, peakPlayers: 12, avgAge: 30.2 },
  { year: 2028, rating: 84, peakPlayers: 8, avgAge: 31.2 },
  { year: 2029, rating: 81, peakPlayers: 5, avgAge: 32.2 },
]

const squadStrengths = [
  { attribute: "Attack", current: 88, potential: 90 },
  { attribute: "Midfield", current: 92, potential: 94 },
  { attribute: "Defense", current: 85, potential: 82 },
  { attribute: "Goalkeeping", current: 89, potential: 87 },
  { attribute: "Depth", current: 91, potential: 88 },
  { attribute: "Experience", current: 87, potential: 85 },
]

const keyPlayers = [
  {
    name: "Erling Haaland",
    position: "Forward",
    age: 24,
    rating: 94,
    peakYears: "2024-2028",
    importance: "Critical",
    image: "/football-player-portrait.png",
  },
  {
    name: "Kevin De Bruyne",
    position: "Midfielder",
    age: 33,
    rating: 91,
    peakYears: "Declining",
    importance: "High",
    image: "/football-player-portrait.png",
  },
  {
    name: "Rodri",
    position: "Midfielder",
    age: 28,
    rating: 89,
    peakYears: "2024-2027",
    importance: "Critical",
    image: "/football-player-portrait.png",
  },
  {
    name: "Phil Foden",
    position: "Midfielder",
    age: 24,
    rating: 88,
    peakYears: "2025-2029",
    importance: "High",
    image: "/football-player-portrait.png",
  },
]

const COLORS = [
  "hsl(var(--primary))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
]

export function TeamAnalysisDashboard() {

  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  const [showCurrent, setShowCurrent] = useState(true)
  const [showPotential, setShowPotential] = useState(true)
  return (
    <div className="space-y-8">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Squad Size</CardTitle>
            <Users className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{squadData.totalPlayers}</div>
            <p className="text-xs text-muted-foreground">Total players</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Age</CardTitle>
            <Calendar className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{squadData.avgAge}</div>
            <p className="text-xs text-muted-foreground">Years old</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Squad Rating</CardTitle>
            <Star className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{squadData.avgRating}</div>
            <p className="text-xs text-muted-foreground">Average rating</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Peak Window</CardTitle>
            <Target className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{squadData.peakWindow}</div>
            <p className="text-xs text-muted-foreground">Optimal performance</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5 bg-secondary/20">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="age">Age Analysis</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="future">Future Outlook</TabsTrigger>
          <TabsTrigger value="players">Key Players</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Squad Strengths & Weaknesses</CardTitle>
                <CardDescription>AI analysis of team attributes</CardDescription>
              </CardHeader>
              <CardContent>
                {/* Radar toggle buttons */}
                <div className="flex space-x-2 mb-4">
                  <button
                    className={`px-3 py-1 rounded border ${showCurrent
                      ? "bg-white text-black border-white"
                      : "bg-transparent text-white border-white"
                      }`}
                    onClick={() => setShowCurrent(!showCurrent)}
                  >
                    Current
                  </button>
                  <button
                    className={`px-3 py-1 rounded border ${showPotential
                      ? "bg-yellow-400 text-black border-yellow-400"
                      : "bg-transparent text-white border-white"
                      }`}
                    onClick={() => setShowPotential(!showPotential)}
                  >
                    Potential
                  </button>
                </div>

                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={squadStrengths}>
                    <PolarGrid stroke="#ffffff33" />
                    <PolarAngleAxis dataKey="attribute" tick={{ fill: "#ffffff", fontSize: 12 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "#ffffff", fontSize: 10 }} />
                    {showCurrent && (
                      <Radar
                        name="Current"
                        dataKey="current"
                        stroke="#ffffff"
                        fill="#ffffff"
                        fillOpacity={0.3}
                        strokeWidth={2}
                      />
                    )}
                    {showPotential && (
                      <Radar
                        name="Potential"
                        dataKey="potential"
                        stroke="#fbbf24"
                        fill="#fbbf24"
                        fillOpacity={0.2}
                        strokeWidth={2}
                        strokeDasharray="5 5"
                      />
                    )}
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Squad Analysis Summary */}
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Squad Analysis Summary</CardTitle>
                <CardDescription>Key insights and recommendations</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h4 className="font-semibold text-primary mb-3">Strengths</h4>
                  <div className="space-y-2">
                    {squadData.strengths.map((strength, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-primary rounded-full" />
                        <span className="text-sm text-foreground">{strength}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold text-destructive mb-3">Areas for Improvement</h4>
                  <div className="space-y-2">
                    {squadData.weaknesses.map((weakness, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <AlertTriangle className="w-4 h-4 text-destructive" />
                        <span className="text-sm text-foreground">{weakness}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
                  <h4 className="font-semibold text-primary mb-2">AI Recommendation</h4>
                  <p className="text-sm text-foreground">
                    Squad is entering peak window. Focus on maintaining midfield excellence while addressing defensive
                    aging. Consider strategic signings in 2025-2026.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="age" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Age Distribution</CardTitle>
                <CardDescription>Squad breakdown by age groups</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={ageDistribution}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="count"
                      labelLine={false}
                      label={({ ageGroup, percentage }) => `${ageGroup}: ${percentage}%`} // keeps labels around pie
                      fill="#fbbf24" // base slice color (gold)
                    >
                      {ageDistribution.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill="#fbbf24"
                          onMouseEnter={(e: any) => e.target.setAttribute("fill", "#d19a00")} // darker yellow on hover
                          onMouseLeave={(e: any) => e.target.setAttribute("fill", "#fbbf24")} // revert color
                        />
                      ))}
                    </Pie>
                    {/* Tooltip removed */}
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Age Group Analysis</CardTitle>
                <CardDescription>Detailed breakdown by age ranges</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {ageDistribution.map((group, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-foreground">{group.ageGroup} years</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-muted-foreground">{group.count} players</span>
                        <Badge variant="secondary" className="bg-primary/10 text-primary">
                          {group.percentage}%
                        </Badge>
                      </div>
                    </div>
                    <Progress value={group.percentage} className="h-2" />
                  </div>
                ))}
                <div className="mt-6 p-4 bg-secondary/20 rounded-lg">
                  <h4 className="font-semibold text-foreground mb-2">Age Analysis</h4>
                  <p className="text-sm text-muted-foreground">
                    Well-balanced squad with 72% of players in their prime years (22-29). The core is mature but not
                    aging, providing stability for the next 3-4 years.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="positions" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>Position Breakdown</CardTitle>
              <CardDescription>Squad composition and quality by position</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={positionBreakdown}
                  margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff33" />
                  <XAxis
                    dataKey="position"
                    stroke="#ffffff"
                    tick={{ fill: "#ffffff", fontSize: 12 }}
                  />
                  <YAxis stroke="#ffffff" tick={{ fill: "#ffffff", fontSize: 12 }} />

                  {/* Bars with labels on top */}
                  <Bar dataKey="count" name="Player Count" fill="#fbbf24">
                    <LabelList dataKey="count" position="top" fill="#ffffff" fontSize={12} />
                  </Bar>
                  <Bar dataKey="avgAge" name="Avg Age" fill="#fcd34d">
                    <LabelList dataKey="avgAge" position="top" fill="#ffffff" fontSize={12} />
                  </Bar>
                  <Bar dataKey="avgRating" name="Avg Rating" fill="#fde68a">
                    <LabelList dataKey="avgRating" position="top" fill="#ffffff" fontSize={12} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {positionBreakdown.map((position, index) => (
              <Card key={index} className="border-border/50 bg-card/80">
                <CardContent className="p-4 text-center">
                  <h3 className="font-semibold text-foreground mb-2">{position.position}</h3>
                  <div className="space-y-2">
                    <div className="text-2xl font-bold text-primary">{position.count}</div>
                    <div className="text-xs text-muted-foreground">Players</div>
                    <div className="text-sm text-muted-foreground">Avg Age: {position.avgAge}</div>
                    <div className="flex items-center justify-center space-x-1">
                      <Star className="h-3 w-3 text-primary fill-current" />
                      <span className="text-sm font-medium">{position.avgRating}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="future" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span>5-Year Performance Projection</span>
              </CardTitle>
              <CardDescription>Predicted squad evolution and performance trends</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={futureProjections}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff33" />
                  <XAxis
                    dataKey="year"
                    stroke="#ffffff"
                    tick={{ fill: "#ffffff", fontSize: 12 }}
                  />
                  <YAxis
                    stroke="#ffffff"
                    tick={{ fill: "#ffffff", fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0, 0, 0, 0.7)", // semi-transparent background
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
                    dataKey="rating"
                    stroke="#ffffff" // white line for rating
                    strokeWidth={3}
                    name="Squad Rating"
                    dot={{ fill: "#ffffff", stroke: "#ffffff", strokeWidth: 2 }} // white dots
                  />
                  <Line
                    type="monotone"
                    dataKey="peakPlayers"
                    stroke="#10b981" // green line for peakPlayers
                    strokeWidth={2}
                    name="Peak Players"
                    dot={{ fill: "#10b981", stroke: "#ffffff", strokeWidth: 2 }} // green dots with white outline
                  />
                </LineChart>
              </ResponsiveContainer>



            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle className="text-lg">2024-2026</CardTitle>
                <CardDescription>Peak Performance Window</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm">Expected Rating</span>
                    <span className="font-semibold text-primary">89-90</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Peak Players</span>
                    <span className="font-semibold text-primary">15-18</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Optimal performance period with most players in their prime years.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle className="text-lg">2027-2028</CardTitle>
                <CardDescription>Transition Period</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm">Expected Rating</span>
                    <span className="font-semibold text-chart-3">84-87</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Peak Players</span>
                    <span className="font-semibold text-chart-3">8-12</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Key players aging out, requiring strategic squad refresh.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle className="text-lg">2029+</CardTitle>
                <CardDescription>Rebuild Phase</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm">Expected Rating</span>
                    <span className="font-semibold text-destructive">81-84</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Peak Players</span>
                    <span className="font-semibold text-destructive">5-8</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Major squad overhaul needed to maintain competitiveness.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="players" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>Key Players Analysis</CardTitle>
              <CardDescription>Critical players and their projected impact</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {keyPlayers.map((player, index) => (
                  <Card key={index} className="border-border/30 bg-secondary/10">
                    <CardContent className="p-4">
                      <div className="flex items-center space-x-4">
                        <img
                          src={player.image || "/placeholder.svg"}
                          alt={player.name}
                          className="w-16 h-16 rounded-full object-cover border-2 border-primary/20"
                        />
                        <div className="flex-1">
                          <h3 className="font-semibold text-foreground">{player.name}</h3>
                          <p className="text-sm text-muted-foreground">{player.position}</p>
                          <div className="flex items-center space-x-3 mt-2">
                            <Badge
                              variant={player.importance === "Critical" ? "default" : "secondary"}
                              className={
                                player.importance === "Critical"
                                  ? "bg-primary text-primary-foreground"
                                  : "bg-chart-2/20 text-chart-2"
                              }
                            >
                              {player.importance}
                            </Badge>
                            <span className="text-xs text-muted-foreground">Age: {player.age}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-primary">{player.rating}</div>
                          <div className="text-xs text-muted-foreground">Rating</div>
                          <div className="text-xs text-muted-foreground mt-1">{player.peakYears}</div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>Squad Recommendations</CardTitle>
              <CardDescription>AI-powered transfer and development suggestions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
                <h4 className="font-semibold text-primary mb-2">Immediate Priorities (2024-2025)</h4>
                <ul className="text-sm text-foreground space-y-1">
                  <li>• Secure long-term contracts for Haaland and Foden</li>
                  <li>• Identify De Bruyne's successor in midfield</li>
                  <li>• Monitor defensive aging and plan replacements</li>
                </ul>
              </div>

              <div className="p-4 bg-secondary/20 rounded-lg">
                <h4 className="font-semibold text-foreground mb-2">Medium-term Strategy (2025-2027)</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Invest in young defensive talents</li>
                  <li>• Develop academy players for squad depth</li>
                  <li>• Consider strategic sales of aging players</li>
                </ul>
              </div>

              <div className="p-4 bg-secondary/20 rounded-lg">
                <h4 className="font-semibold text-foreground mb-2">Long-term Vision (2027+)</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Complete squad refresh around core young players</li>
                  <li>• Maintain competitive standards during transition</li>
                  <li>• Build new tactical identity for next generation</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
