"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Search, Star, ArrowRight, Shuffle } from "lucide-react"

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
  {
    id: 5,
    name: "Virgil van Dijk",
    team: "Liverpool",
    position: "Defender",
    age: 32,
    rating: 89,
    image: "/football-player-portrait.png",
  },
  {
    id: 6,
    name: "Luka Modrić",
    team: "Real Madrid",
    position: "Midfielder",
    age: 38,
    rating: 88,
    image: "/football-player-portrait.png",
  },
]

export function PlayerSelector() {
  const [searchTerm1, setSearchTerm1] = useState("")
  const [searchTerm2, setSearchTerm2] = useState("")
  const [selectedPlayer1, setSelectedPlayer1] = useState(mockPlayers[0])
  const [selectedPlayer2, setSelectedPlayer2] = useState(mockPlayers[1])
  const [showSearch1, setShowSearch1] = useState(false)
  const [showSearch2, setShowSearch2] = useState(false)

  const filteredPlayers1 = mockPlayers.filter(
    (player) => player.name.toLowerCase().includes(searchTerm1.toLowerCase()) && player.id !== selectedPlayer2?.id,
  )
  const filteredPlayers2 = mockPlayers.filter(
    (player) => player.name.toLowerCase().includes(searchTerm2.toLowerCase()) && player.id !== selectedPlayer1?.id,
  )

  const handlePlayerSelect1 = (player: any) => {
    setSelectedPlayer1(player)
    setShowSearch1(false)
    setSearchTerm1("")
  }

  const handlePlayerSelect2 = (player: any) => {
    setSelectedPlayer2(player)
    setShowSearch2(false)
    setSearchTerm2("")
  }

  const swapPlayers = () => {
    const temp = selectedPlayer1
    setSelectedPlayer1(selectedPlayer2)
    setSelectedPlayer2(temp)
  }

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
        {/* Player 1 */}
        <div className="space-y-4">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-foreground mb-2">Player 1</h3>
            {!showSearch1 ? (
              <Card className="border-primary/30 bg-card/90 cursor-pointer" onClick={() => setShowSearch1(true)}>
                <CardContent className="p-6">
                  <div className="text-center space-y-4">
                    <img
                      src={selectedPlayer1?.image || "/placeholder.svg"}
                      alt={selectedPlayer1?.name}
                      className="w-20 h-20 rounded-full object-cover border-3 border-primary mx-auto"
                    />
                    <div>
                      <h3 className="text-xl font-bold text-foreground">{selectedPlayer1?.name}</h3>
                      <p className="text-muted-foreground">{selectedPlayer1?.team}</p>
                      <div className="flex items-center justify-center space-x-4 mt-2">
                        <Badge className="bg-primary text-primary-foreground">{selectedPlayer1?.position}</Badge>
                        <span className="text-sm text-muted-foreground">Age: {selectedPlayer1?.age}</span>
                        <div className="flex items-center space-x-1">
                          <Star className="h-4 w-4 text-primary fill-current" />
                          <span className="font-medium">{selectedPlayer1?.rating}</span>
                        </div>
                      </div>
                    </div>
                    <Button variant="outline" className="border-primary/30 hover:bg-primary/10 bg-transparent">
                      Change Player
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-5 w-5" />
                  <Input
                    placeholder="Search for player 1..."
                    value={searchTerm1}
                    onChange={(e) => setSearchTerm1(e.target.value)}
                    className="pl-10 h-12 bg-card border-border/50"
                  />
                </div>
                <div className="max-h-64 overflow-y-auto space-y-2">
                  {filteredPlayers1.map((player) => (
                    <Card
                      key={player.id}
                      className="cursor-pointer hover:shadow-lg transition-all duration-300 border-border/50 bg-card/80"
                      onClick={() => handlePlayerSelect1(player)}
                    >
                      <CardContent className="p-3">
                        <div className="flex items-center space-x-3">
                          <img
                            src={player.image || "/placeholder.svg"}
                            alt={player.name}
                            className="w-12 h-12 rounded-full object-cover border-2 border-primary/20"
                          />
                          <div className="flex-1">
                            <h4 className="font-semibold text-foreground">{player.name}</h4>
                            <p className="text-sm text-muted-foreground">{player.team}</p>
                          </div>
                          <div className="text-right">
                            <Badge variant="secondary" className="bg-primary/10 text-primary text-xs">
                              {player.position}
                            </Badge>
                            <div className="flex items-center space-x-1 mt-1">
                              <Star className="h-3 w-3 text-primary fill-current" />
                              <span className="text-xs font-medium">{player.rating}</span>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
                <Button
                  variant="outline"
                  onClick={() => setShowSearch1(false)}
                  className="w-full border-border/50 hover:bg-secondary/20"
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* VS and Swap */}
        <div className="flex flex-col items-center space-y-4">
          <div className="text-4xl font-bold text-primary">VS</div>
          <Button
            variant="outline"
            size="sm"
            onClick={swapPlayers}
            className="border-primary/30 hover:bg-primary/10 bg-transparent"
          >
            <Shuffle className="h-4 w-4 mr-2" />
            Swap
          </Button>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
            <ArrowRight className="h-4 w-4 mr-2" />
            Compare
          </Button>
        </div>

        {/* Player 2 */}
        <div className="space-y-4">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-foreground mb-2">Player 2</h3>
            {!showSearch2 ? (
              <Card className="border-chart-2/30 bg-card/90 cursor-pointer" onClick={() => setShowSearch2(true)}>
                <CardContent className="p-6">
                  <div className="text-center space-y-4">
                    <img
                      src={selectedPlayer2?.image || "/placeholder.svg"}
                      alt={selectedPlayer2?.name}
                      className="w-20 h-20 rounded-full object-cover border-3 border-chart-2 mx-auto"
                    />
                    <div>
                      <h3 className="text-xl font-bold text-foreground">{selectedPlayer2?.name}</h3>
                      <p className="text-muted-foreground">{selectedPlayer2?.team}</p>
                      <div className="flex items-center justify-center space-x-4 mt-2">
                        <Badge className="bg-chart-2 text-primary-foreground">{selectedPlayer2?.position}</Badge>
                        <span className="text-sm text-muted-foreground">Age: {selectedPlayer2?.age}</span>
                        <div className="flex items-center space-x-1">
                          <Star className="h-4 w-4 text-chart-2 fill-current" />
                          <span className="font-medium">{selectedPlayer2?.rating}</span>
                        </div>
                      </div>
                    </div>
                    <Button variant="outline" className="border-chart-2/30 hover:bg-chart-2/10 bg-transparent">
                      Change Player
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-5 w-5" />
                  <Input
                    placeholder="Search for player 2..."
                    value={searchTerm2}
                    onChange={(e) => setSearchTerm2(e.target.value)}
                    className="pl-10 h-12 bg-card border-border/50"
                  />
                </div>
                <div className="max-h-64 overflow-y-auto space-y-2">
                  {filteredPlayers2.map((player) => (
                    <Card
                      key={player.id}
                      className="cursor-pointer hover:shadow-lg transition-all duration-300 border-border/50 bg-card/80"
                      onClick={() => handlePlayerSelect2(player)}
                    >
                      <CardContent className="p-3">
                        <div className="flex items-center space-x-3">
                          <img
                            src={player.image || "/placeholder.svg"}
                            alt={player.name}
                            className="w-12 h-12 rounded-full object-cover border-2 border-chart-2/20"
                          />
                          <div className="flex-1">
                            <h4 className="font-semibold text-foreground">{player.name}</h4>
                            <p className="text-sm text-muted-foreground">{player.team}</p>
                          </div>
                          <div className="text-right">
                            <Badge variant="secondary" className="bg-chart-2/10 text-chart-2 text-xs">
                              {player.position}
                            </Badge>
                            <div className="flex items-center space-x-1 mt-1">
                              <Star className="h-3 w-3 text-chart-2 fill-current" />
                              <span className="text-xs font-medium">{player.rating}</span>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
                <Button
                  variant="outline"
                  onClick={() => setShowSearch2(false)}
                  className="w-full border-border/50 hover:bg-secondary/20"
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
