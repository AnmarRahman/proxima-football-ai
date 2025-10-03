"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Search, Settings, Star, Filter } from "lucide-react"

const mockPlayers = [
  {
    id: 1,
    name: "Kylian Mbappé",
    team: "Paris Saint-Germain",
    position: "Forward",
    age: 25,
    rating: 95,
    image: "/football-player-portrait.png",
  },
  {
    id: 2,
    name: "Erling Haaland",
    team: "Manchester City",
    position: "Forward",
    age: 24,
    rating: 94,
    image: "/football-player-portrait.png",
  },
  {
    id: 3,
    name: "Jude Bellingham",
    team: "Real Madrid",
    position: "Midfielder",
    age: 21,
    rating: 90,
    image: "/football-player-portrait.png",
  },
  {
    id: 4,
    name: "Kevin De Bruyne",
    team: "Manchester City",
    position: "Midfielder",
    age: 33,
    rating: 91,
    image: "/football-player-portrait.png",
  },
]

export function SimilaritySearch() {
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedPlayer, setSelectedPlayer] = useState(mockPlayers[0])
  const [ageRange, setAgeRange] = useState([18, 40])
  const [eraFilter, setEraFilter] = useState("all")
  const [positionFilter, setPositionFilter] = useState("all")

  const filteredPlayers = mockPlayers.filter((player) => player.name.toLowerCase().includes(searchTerm.toLowerCase()))

  return (
    <div className="space-y-8">
      <div className="max-w-2xl mx-auto">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-5 w-5" />
          <Input
            placeholder="Search for a player to find similarities..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 h-12 text-lg bg-card border-border/50"
          />
        </div>
      </div>

      {searchTerm && (
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {filteredPlayers.map((player) => (
              <Card
                key={player.id}
                className={`cursor-pointer transition-all duration-300 border-border/50 bg-card/80 ${
                  selectedPlayer.id === player.id ? "border-primary shadow-lg shadow-primary/20" : "hover:shadow-lg"
                }`}
                onClick={() => setSelectedPlayer(player)}
              >
                <CardContent className="p-4">
                  <div className="text-center space-y-3">
                    <img
                      src={player.image || "/placeholder.svg"}
                      alt={player.name}
                      className="w-16 h-16 rounded-full object-cover border-2 border-primary/20 mx-auto"
                    />
                    <div>
                      <h3 className="font-semibold text-foreground">{player.name}</h3>
                      <p className="text-sm text-muted-foreground">{player.team}</p>
                      <div className="flex items-center justify-center space-x-2 mt-2">
                        <Badge variant="secondary" className="bg-primary/10 text-primary text-xs">
                          {player.position}
                        </Badge>
                        <div className="flex items-center space-x-1">
                          <Star className="h-3 w-3 text-primary fill-current" />
                          <span className="text-xs font-medium">{player.rating}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {selectedPlayer && (
        <div className="max-w-6xl mx-auto">
          <Card className="border-primary/30 bg-card/90">
            <CardContent className="p-6">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-6 lg:space-y-0">
                <div className="flex items-center space-x-6">
                  <img
                    src={selectedPlayer.image || "/placeholder.svg"}
                    alt={selectedPlayer.name}
                    className="w-20 h-20 rounded-full object-cover border-3 border-primary"
                  />
                  <div>
                    <h2 className="text-2xl font-bold text-foreground">{selectedPlayer.name}</h2>
                    <p className="text-muted-foreground">{selectedPlayer.team}</p>
                    <div className="flex items-center space-x-4 mt-2">
                      <Badge className="bg-primary text-primary-foreground">{selectedPlayer.position}</Badge>
                      <span className="text-sm text-muted-foreground">Age: {selectedPlayer.age}</span>
                      <div className="flex items-center space-x-1">
                        <Star className="h-4 w-4 text-primary fill-current" />
                        <span className="font-medium">{selectedPlayer.rating}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-4">
                  <Tabs defaultValue="basic" className="w-full sm:w-auto">
                    <TabsList className="grid w-full grid-cols-2 bg-secondary/20">
                      <TabsTrigger value="basic" className="flex items-center space-x-2">
                        <Search className="h-4 w-4" />
                        <span>Basic Search</span>
                      </TabsTrigger>
                      <TabsTrigger value="advanced" className="flex items-center space-x-2">
                        <Settings className="h-4 w-4" />
                        <span>Advanced</span>
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="basic" className="mt-4">
                      <Button className="bg-primary text-primary-foreground hover:bg-primary/90 w-full sm:w-auto">
                        Find Similar Players
                      </Button>
                    </TabsContent>

                    <TabsContent value="advanced" className="mt-4 space-y-4 min-w-80">
                      <div className="space-y-4 p-4 bg-secondary/10 rounded-lg">
                        <div className="space-y-2">
                          <Label className="text-sm font-medium">Age Range</Label>
                          <Slider
                            value={ageRange}
                            onValueChange={setAgeRange}
                            max={40}
                            min={18}
                            step={1}
                            className="w-full"
                          />
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>{ageRange[0]} years</span>
                            <span>{ageRange[1]} years</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <Label className="text-sm font-medium">Era</Label>
                            <select
                              value={eraFilter}
                              onChange={(e) => setEraFilter(e.target.value)}
                              className="w-full mt-1 p-2 bg-background border border-border rounded-md text-sm"
                            >
                              <option value="all">All Time</option>
                              <option value="current">Current (2020+)</option>
                              <option value="modern">Modern (2010+)</option>
                              <option value="classic">Classic (2000-2010)</option>
                            </select>
                          </div>
                          <div>
                            <Label className="text-sm font-medium">Position</Label>
                            <select
                              value={positionFilter}
                              onChange={(e) => setPositionFilter(e.target.value)}
                              className="w-full mt-1 p-2 bg-background border border-border rounded-md text-sm"
                            >
                              <option value="all">All Positions</option>
                              <option value="forward">Forward</option>
                              <option value="midfielder">Midfielder</option>
                              <option value="defender">Defender</option>
                              <option value="goalkeeper">Goalkeeper</option>
                            </select>
                          </div>
                        </div>

                        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 w-full">
                          <Filter className="h-4 w-4 mr-2" />
                          Find with Filters
                        </Button>
                      </div>
                    </TabsContent>
                  </Tabs>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
