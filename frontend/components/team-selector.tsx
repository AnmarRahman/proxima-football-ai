"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Search, Star, Trophy, Users } from "lucide-react"
import { useState } from "react"

const mockTeams = [
  {
    id: 1,
    name: "Manchester City",
    league: "Premier League",
    country: "England",
    rating: 89,
    logo: "/team-logo.png",
    players: 25,
    avgAge: 27.2,
    marketValue: "€1.2B",
  },
  {
    id: 2,
    name: "Real Madrid",
    league: "La Liga",
    country: "Spain",
    rating: 88,
    logo: "/team-logo.png",
    players: 26,
    avgAge: 26.8,
    marketValue: "€1.1B",
  },
  {
    id: 3,
    name: "Paris Saint-Germain",
    league: "Ligue 1",
    country: "France",
    rating: 87,
    logo: "/team-logo.png",
    players: 24,
    avgAge: 26.5,
    marketValue: "€950M",
  },
  {
    id: 4,
    name: "Bayern Munich",
    league: "Bundesliga",
    country: "Germany",
    rating: 86,
    logo: "/team-logo.png",
    players: 25,
    avgAge: 27.8,
    marketValue: "€900M",
  },
  {
    id: 5,
    name: "Arsenal",
    league: "Premier League",
    country: "England",
    rating: 85,
    logo: "/team-logo.png",
    players: 26,
    avgAge: 25.9,
    marketValue: "€850M",
  },
  {
    id: 6,
    name: "Barcelona",
    league: "La Liga",
    country: "Spain",
    rating: 84,
    logo: "/team-logo.png",
    players: 25,
    avgAge: 26.1,
    marketValue: "€800M",
  },
]

export function TeamSelector() {
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedTeam, setSelectedTeam] = useState(mockTeams[0])
  const [showSearch, setShowSearch] = useState(false)

  const filteredTeams = mockTeams.filter((team) => team.name.toLowerCase().includes(searchTerm.toLowerCase()))

  const handleTeamSelect = (team: any) => {
    setSelectedTeam(team)
    setShowSearch(false)
    setSearchTerm("")
  }

  return (
    <div className="space-y-8">
      <div className="max-w-2xl mx-auto">
        {!showSearch ? (
          <Card className="border-primary/30 bg-card/90 cursor-pointer" onClick={() => setShowSearch(true)}>
            <CardContent className="p-6">
              <div className="flex items-center space-x-6">
                <img
                  src={selectedTeam?.logo || "/placeholder.svg"}
                  alt={selectedTeam?.name}
                  className="w-20 h-20 rounded-full object-cover border-3 border-primary"
                />
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-foreground">{selectedTeam?.name}</h2>
                  <p className="text-muted-foreground">{selectedTeam?.league}</p>
                  <div className="flex items-center space-x-4 mt-2">
                    <Badge className="bg-primary text-primary-foreground">{selectedTeam?.country}</Badge>
                    <div className="flex items-center space-x-1">
                      <Star className="h-4 w-4 text-primary fill-current" />
                      <span className="font-medium">{selectedTeam?.rating}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right space-y-2">
                  <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                    <Users className="h-4 w-4" />
                    <span>{selectedTeam?.players} players</span>
                  </div>
                  <div className="text-sm text-muted-foreground">Avg Age: {selectedTeam?.avgAge}</div>
                  <div className="text-sm font-medium text-primary">{selectedTeam?.marketValue}</div>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-border">
                <Button variant="outline" className="w-full border-primary/30 hover:bg-primary/10 bg-transparent">
                  Change Team
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-5 w-5" />
              <Input
                placeholder="Search for a team..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 h-12 text-lg bg-card border-border/50"
              />
            </div>
            <div className="max-h-96 overflow-y-auto space-y-3">
              {filteredTeams.map((team) => (
                <Card
                  key={team.id}
                  className="cursor-pointer hover:shadow-lg hover:shadow-primary/10 transition-all duration-300 border-border/50 bg-card/80"
                  onClick={() => handleTeamSelect(team)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-4">
                      <img
                        src={team.logo || "/placeholder.svg"}
                        alt={team.name}
                        className="w-16 h-16 rounded-full object-cover border-2 border-primary/20"
                      />
                      <div className="flex-1">
                        <h3 className="font-semibold text-foreground">{team.name}</h3>
                        <p className="text-sm text-muted-foreground">{team.league}</p>
                        <div className="flex items-center space-x-3 mt-2">
                          <Badge variant="secondary" className="bg-primary/10 text-primary text-xs">
                            {team.country}
                          </Badge>
                          <div className="flex items-center space-x-1">
                            <Star className="h-3 w-3 text-primary fill-current" />
                            <span className="text-xs font-medium">{team.rating}</span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium text-primary">{team.marketValue}</div>
                        <div className="text-xs text-muted-foreground">{team.players} players</div>
                        <div className="text-xs text-muted-foreground">Avg: {team.avgAge}y</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            <Button
              variant="outline"
              onClick={() => setShowSearch(false)}
              className="w-full border-border/50 hover:bg-secondary/20"
            >
              Cancel
            </Button>
          </div>
        )}
      </div>

      {selectedTeam && !showSearch && (
        <div className="text-center">
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90 text-lg px-8 py-3 mb-8">
            <Trophy className="h-5 w-5 mr-2" />
            Analyze Squad
          </Button>
        </div>
      )}
    </div>
  )
}
