"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowRight, Calendar, Target, TrendingUp, Users } from "lucide-react"
import { useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts"

const similarPlayers = [
  {
    id: 1,
    name: "Thierry Henry",
    team: "Arsenal (Peak)",
    position: "Forward",
    era: "2000-2010",
    similarity: 94,
    image: "/football-player-portrait.png",
    keyStats: { goals: 228, assists: 103, trophies: 15 },
    similarities: ["Pace", "Finishing", "Movement", "Left Foot"],
    differences: ["Height", "Physicality"],
  },
  {
    id: 2,
    name: "Ronaldo Nazário",
    team: "Real Madrid (Peak)",
    position: "Forward",
    era: "1990-2010",
    similarity: 91,
    image: "/football-player-portrait.png",
    keyStats: { goals: 352, assists: 89, trophies: 18 },
    similarities: ["Pace", "Dribbling", "Clinical Finishing"],
    differences: ["Injury Proneness", "Playing Style"],
  },
  {
    id: 3,
    name: "Karim Benzema",
    team: "Real Madrid",
    position: "Forward",
    era: "2010-2023",
    similarity: 87,
    image: "/football-player-portrait.png",
    keyStats: { goals: 354, assists: 165, trophies: 25 },
    similarities: ["Link-up Play", "Big Game Performance"],
    differences: ["Pace", "Playing Position"],
  },
  {
    id: 4,
    name: "Neymar Jr.",
    team: "Barcelona (Peak)",
    position: "Forward/Winger",
    era: "2010-Present",
    similarity: 85,
    image: "/football-player-portrait.png",
    keyStats: { goals: 287, assists: 178, trophies: 19 },
    similarities: ["Dribbling", "Creativity", "Flair"],
    differences: ["Pace", "Physicality", "Consistency"],
  },
  {
    id: 5,
    name: "Samuel Eto'o",
    team: "Barcelona (Peak)",
    position: "Forward",
    era: "2000-2015",
    similarity: 83,
    image: "/football-player-portrait.png",
    keyStats: { goals: 359, assists: 87, trophies: 20 },
    similarities: ["Pace", "Movement", "Big Game Goals"],
    differences: ["Height", "Playing Style"],
  },
]

const attributeComparison = [
  { attribute: "Pace", mbappe: 95, similar: 92 },
  { attribute: "Shooting", mbappe: 92, similar: 94 },
  { attribute: "Passing", mbappe: 85, similar: 88 },
  { attribute: "Dribbling", mbappe: 94, similar: 91 },
  { attribute: "Physical", mbappe: 88, similar: 85 },
  { attribute: "Mental", mbappe: 89, similar: 93 },
]

const careerComparison = [
  { age: 21, mbappe: 42, similar: 38 },
  { age: 22, mbappe: 39, similar: 45 },
  { age: 23, mbappe: 44, similar: 52 },
  { age: 24, mbappe: 41, similar: 48 },
  { age: 25, mbappe: 44, similar: 51 },
]

export function SimilarityResults() {
  const [showPlayer1, setShowPlayer1] = useState(true)
  const [showPlayer2, setShowPlayer2] = useState(true)

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-foreground mb-2">Most Similar Players</h2>
        <p className="text-muted-foreground">Based on playing style, attributes, and career patterns</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {similarPlayers.map((player) => (
          <Card
            key={player.id}
            className="group hover:shadow-xl hover:shadow-primary/10 transition-all duration-300 border-border/50 bg-card/80"
          >
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <img
                    src={player.image || "/placeholder.svg"}
                    alt={player.name}
                    className="w-12 h-12 rounded-full object-cover border-2 border-primary/20"
                  />
                  <div>
                    <CardTitle className="text-lg group-hover:text-primary transition-colors">{player.name}</CardTitle>
                    <CardDescription className="text-sm">{player.team}</CardDescription>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-primary">{player.similarity}%</div>
                  <div className="text-xs text-muted-foreground">Similarity</div>
                </div>
              </div>
              <Progress value={player.similarity} className="h-2" />
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <Badge variant="secondary" className="bg-primary/10 text-primary">
                  {player.position}
                </Badge>
                <span className="text-muted-foreground">{player.era}</span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 bg-secondary/20 rounded">
                  <div className="font-semibold text-primary">{player.keyStats.goals}</div>
                  <div className="text-xs text-muted-foreground">Goals</div>
                </div>
                <div className="p-2 bg-secondary/20 rounded">
                  <div className="font-semibold text-primary">{player.keyStats.assists}</div>
                  <div className="text-xs text-muted-foreground">Assists</div>
                </div>
                <div className="p-2 bg-secondary/20 rounded">
                  <div className="font-semibold text-primary">{player.keyStats.trophies}</div>
                  <div className="text-xs text-muted-foreground">Trophies</div>
                </div>
              </div>

              <div className="space-y-2">
                <div>
                  <h4 className="text-sm font-medium text-foreground mb-1">Key Similarities</h4>
                  <div className="flex flex-wrap gap-1">
                    {player.similarities.map((sim, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs border-primary/30 text-primary">
                        {sim}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-foreground mb-1">Key Differences</h4>
                  <div className="flex flex-wrap gap-1">
                    {player.differences.map((diff, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs border-muted text-muted-foreground">
                        {diff}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              <Button variant="outline" className="w-full border-primary/30 hover:bg-primary/10 bg-transparent">
                View Detailed Comparison
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="attributes" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3 bg-secondary/20">
          <TabsTrigger value="attributes">Attribute Analysis</TabsTrigger>
          <TabsTrigger value="career">Career Patterns</TabsTrigger>
          <TabsTrigger value="insights">AI Insights</TabsTrigger>
        </TabsList>

        <TabsContent value="attributes" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border-border/50 bg-card/80">
              <CardHeader>
                <CardTitle>Attribute Comparison</CardTitle>
                <CardDescription>Mbappé vs Most Similar Player (Thierry Henry)</CardDescription>
                <div className="flex items-center space-x-4 mt-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="player1"
                      checked={showPlayer1}
                      onCheckedChange={(checked) => setShowPlayer1(checked === true)}
                    />
                    <label htmlFor="player1" className="text-sm font-medium text-primary">
                      Mbappé
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="player2"
                      checked={showPlayer2}
                      onCheckedChange={(checked) => setShowPlayer2(checked === true)}
                    />
                    <label htmlFor="player2" className="text-sm font-medium text-chart-2">
                      Thierry Henry
                    </label>
                  </div>
                </div>

              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={attributeComparison}>
                    <PolarGrid stroke="hsl(var(--border))" />
                    <PolarAngleAxis dataKey="attribute" tick={{ fill: "white", fontSize: 12 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "white", fontSize: 10 }} />

                    {showPlayer1 && (
                      <Radar
                        name="Mbappé"
                        dataKey="mbappe"
                        stroke="#fbbf24"
                        fill="#fbbf24"
                        fillOpacity={0.2}
                        strokeWidth={2}
                      />
                    )}

                    {showPlayer2 && (
                      <Radar
                        name="Similar Player"
                        dataKey="similar"
                        stroke="#ffffff"
                        fill="#ffffff"
                        fillOpacity={0.2}
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
                <CardTitle>Similarity Breakdown</CardTitle>
                <CardDescription>How the AI calculates player similarity</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Playing Style</span>
                    <span className="text-sm text-primary font-semibold">96%</span>
                  </div>
                  <Progress value={96} className="h-2" />
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Physical Attributes</span>
                    <span className="text-sm text-primary font-semibold">92%</span>
                  </div>
                  <Progress value={92} className="h-2" />
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Career Trajectory</span>
                    <span className="text-sm text-primary font-semibold">89%</span>
                  </div>
                  <Progress value={89} className="h-2" />
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Statistical Output</span>
                    <span className="text-sm text-primary font-semibold">95%</span>
                  </div>
                  <Progress value={95} className="h-2" />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="career" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span>Career Pattern Comparison</span>
              </CardTitle>
              <CardDescription>Goals per season at similar ages</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={careerComparison} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="age" stroke="#ffffff" tick={{ fill: "#ffffff", fontSize: 12 }} />
                  <YAxis stroke="#ffffff" tick={{ fill: "#ffffff", fontSize: 12 }} />

                  {/* Legend at top-right */}
                  <Legend verticalAlign="top" align="right" wrapperStyle={{ color: "#ffffff" }} />

                  {/* Bars with different colors */}
                  <Bar dataKey="mbappe" fill="#fbbf24" name="Mbappé">
                    <LabelList dataKey="mbappe" position="top" fill="#ffffff" fontSize={12} />
                  </Bar>

                  <Bar dataKey="similar" fill="#22c55e" name="Similar Players Avg">
                    <LabelList dataKey="similar" position="top" fill="#ffffff" fontSize={12} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>


        <TabsContent value="insights" className="space-y-6">
          <Card className="border-border/50 bg-card/80">
            <CardHeader>
              <CardTitle>AI Similarity Analysis</CardTitle>
              <CardDescription>Deep insights into player comparisons</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-primary/10 rounded-lg border border-primary/20">
                  <Users className="h-8 w-8 text-primary mx-auto mb-2" />
                  <div className="text-2xl font-bold text-primary">847</div>
                  <div className="text-sm text-muted-foreground">Players Analyzed</div>
                </div>
                <div className="text-center p-4 bg-secondary/20 rounded-lg">
                  <Target className="h-8 w-8 text-primary mx-auto mb-2" />
                  <div className="text-2xl font-bold text-primary">94%</div>
                  <div className="text-sm text-muted-foreground">Match Confidence</div>
                </div>
                <div className="text-center p-4 bg-secondary/20 rounded-lg">
                  <Calendar className="h-8 w-8 text-primary mx-auto mb-2" />
                  <div className="text-2xl font-bold text-primary">25</div>
                  <div className="text-sm text-muted-foreground">Years of Data</div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
                  <h3 className="font-semibold text-primary mb-2">Strongest Match: Thierry Henry</h3>
                  <p className="text-sm text-foreground">
                    The AI identifies Thierry Henry as the closest historical match to Mbappé's playing style. Both
                    players share exceptional pace, clinical finishing, and the ability to drift wide before cutting
                    inside. Their movement patterns and goal-scoring instincts show remarkable similarity.
                  </p>
                </div>

                <div className="p-4 bg-secondary/20 rounded-lg">
                  <h3 className="font-semibold text-foreground mb-2">Key Differentiators</h3>
                  <p className="text-sm text-muted-foreground">
                    While Henry was more of a complete striker who could create and score, Mbappé's raw pace and
                    directness set him apart. Mbappé's ability to accelerate past defenders is unmatched in the modern
                    game, making him unique even among similar players.
                  </p>
                </div>

                <div className="p-4 bg-secondary/20 rounded-lg">
                  <h3 className="font-semibold text-foreground mb-2">Career Trajectory Insights</h3>
                  <p className="text-sm text-muted-foreground">
                    Based on similar players' career paths, Mbappé is likely to maintain his explosive pace until age
                    28-29, then evolve into a more complete forward like Benzema. His goal output should peak between
                    ages 26-28, similar to Henry's prime years.
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
