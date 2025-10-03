"use client"

import { Header } from "@/components/header"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Clock, Heart, MessageCircle, Share2, TrendingUp, Trophy, Users } from "lucide-react"
import { useState } from "react"

// Mock data for polls and discussions
const mockPolls = [
  {
    id: 1,
    question: "Who will win the Champions League this season?",
    options: [
      { text: "Manchester City", votes: 1250, percentage: 35 },
      { text: "Real Madrid", votes: 1100, percentage: 31 },
      { text: "Bayern Munich", votes: 750, percentage: 21 },
      { text: "PSG", votes: 450, percentage: 13 },
    ],
    totalVotes: 3550,
    timeLeft: "2 days",
    category: "Champions League",
  },
  {
    id: 2,
    question: "Best signing of the summer transfer window?",
    options: [
      { text: "Kylian Mbappé to Real Madrid", votes: 2100, percentage: 42 },
      { text: "Erling Haaland to Man City", votes: 1800, percentage: 36 },
      { text: "Darwin Núñez to Liverpool", votes: 650, percentage: 13 },
      { text: "Sadio Mané to Bayern", votes: 450, percentage: 9 },
    ],
    totalVotes: 5000,
    timeLeft: "5 hours",
    category: "Transfers",
  },
]

const mockDiscussions = [
  {
    id: 1,
    title: "Is Messi still the GOAT after the World Cup win?",
    author: "FootballFan2023",
    replies: 247,
    likes: 1850,
    timeAgo: "2 hours ago",
    category: "GOAT Debate",
    preview: "After that incredible World Cup performance, I think the debate is finally settled...",
  },
  {
    id: 2,
    title: "Premier League predictions for this weekend",
    author: "PremierPredictor",
    replies: 89,
    likes: 432,
    timeAgo: "4 hours ago",
    category: "Predictions",
    preview: "Here are my bold predictions for the upcoming fixtures. City to drop points?",
  },
  {
    id: 3,
    title: "Why Barcelona's rebuild is ahead of schedule",
    author: "CulerAnalyst",
    replies: 156,
    likes: 678,
    timeAgo: "6 hours ago",
    category: "Analysis",
    preview: "Xavi has transformed this team faster than anyone expected. Here's why...",
  },
]

export default function CommunityPage() {
  const [votedPolls, setVotedPolls] = useState<Set<number>>(new Set())

  const handleVote = (pollId: number, optionIndex: number) => {
    setVotedPolls((prev) => new Set(prev).add(pollId))
    // In a real app, this would send the vote to the backend
  }

  return (
    <main className="min-h-screen">
      <Header />
      <div>
        <div className="min-h-screen bg-black text-white">
          <div className="container mx-auto px-4 py-8 pt-10">
            {/* Header */}
            <div className="text-center mb-12">
              <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">
                Fan Community
              </h1>
              <p className="text-xl text-gray-300 max-w-2xl mx-auto">
                Join the conversation, vote on hot topics, and connect with football fans worldwide
              </p>
            </div>

            {/* Community Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <Card className="bg-gray-900 border-gray-800">
                <CardContent className="p-6 text-center">
                  <Users className="h-8 w-8 text-yellow-400 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-white">125K</div>
                  <div className="text-sm text-gray-400">Active Members</div>
                </CardContent>
              </Card>
              <Card className="bg-gray-900 border-gray-800">
                <CardContent className="p-6 text-center">
                  <MessageCircle className="h-8 w-8 text-yellow-400 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-white">8.2K</div>
                  <div className="text-sm text-gray-400">Discussions Today</div>
                </CardContent>
              </Card>
              <Card className="bg-gray-900 border-gray-800">
                <CardContent className="p-6 text-center">
                  <TrendingUp className="h-8 w-8 text-yellow-400 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-white">45K</div>
                  <div className="text-sm text-gray-400">Votes Cast</div>
                </CardContent>
              </Card>
              <Card className="bg-gray-900 border-gray-800">
                <CardContent className="p-6 text-center">
                  <Trophy className="h-8 w-8 text-yellow-400 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-white">12</div>
                  <div className="text-sm text-gray-400">Active Polls</div>
                </CardContent>
              </Card>
            </div>

            <Tabs defaultValue="polls" className="w-full">
              <TabsList className="grid w-full grid-cols-2 bg-gray-900">
                <TabsTrigger value="polls" className="data-[state=active]:bg-yellow-400 data-[state=active]:text-black">
                  Live Polls
                </TabsTrigger>
                <TabsTrigger
                  value="discussions"
                  className="data-[state=active]:bg-yellow-400 data-[state=active]:text-black"
                >
                  Discussions
                </TabsTrigger>
              </TabsList>

              <TabsContent value="polls" className="space-y-6">
                <div className="grid gap-6">
                  {mockPolls.map((poll) => (
                    <Card key={poll.id} className="bg-gray-900 border-gray-800">
                      <CardHeader>
                        <div className="flex justify-between items-start">
                          <div>
                            <CardTitle className="text-xl text-white mb-2">{poll.question}</CardTitle>
                            <div className="flex items-center gap-4 text-sm text-gray-400">
                              <Badge variant="outline" className="border-yellow-400 text-yellow-400">
                                {poll.category}
                              </Badge>
                              <div className="flex items-center gap-1">
                                <Clock className="h-4 w-4" />
                                {poll.timeLeft} left
                              </div>
                              <div className="flex items-center gap-1">
                                <Users className="h-4 w-4" />
                                {poll.totalVotes.toLocaleString()} votes
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          {poll.options.map((option, index) => (
                            <div key={index} className="space-y-2">
                              <div className="flex justify-between items-center">
                                <span className="text-white">{option.text}</span>
                                <span className="text-yellow-400 font-semibold">{option.percentage}%</span>
                              </div>
                              <div className="relative">
                                <Progress value={option.percentage} className="h-3 bg-gray-800" />
                                <div
                                  className="absolute top-0 left-0 h-3 bg-gradient-to-r from-yellow-400 to-yellow-600 rounded-full transition-all duration-500"
                                  style={{ width: `${option.percentage}%` }}
                                />
                              </div>
                              <div className="text-sm text-gray-400">{option.votes.toLocaleString()} votes</div>
                            </div>
                          ))}

                          {!votedPolls.has(poll.id) && (
                            <div className="pt-4 border-t border-gray-800">
                              <div className="grid grid-cols-2 gap-2">
                                {poll.options.map((option, index) => (
                                  <Button
                                    key={index}
                                    variant="outline"
                                    className="border-yellow-400 text-yellow-400 hover:bg-yellow-400 hover:text-black bg-transparent"
                                    onClick={() => handleVote(poll.id, index)}
                                  >
                                    Vote: {option.text}
                                  </Button>
                                ))}
                              </div>
                            </div>
                          )}

                          {votedPolls.has(poll.id) && (
                            <div className="pt-4 border-t border-gray-800">
                              <div className="text-center text-yellow-400 font-semibold">
                                Thanks for voting! Results will be final in {poll.timeLeft}
                              </div>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="discussions" className="space-y-6">
                <div className="grid gap-6">
                  {mockDiscussions.map((discussion) => (
                    <Card
                      key={discussion.id}
                      className="bg-gray-900 border-gray-800 hover:border-yellow-400/50 transition-colors cursor-pointer"
                    >
                      <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                          <Avatar className="h-12 w-12">
                            <AvatarImage
                              src={`/placeholder-icon.png?height=48&width=48&text=${discussion.author[0]}`}
                            />
                            <AvatarFallback className="bg-yellow-400 text-black">{discussion.author[0]}</AvatarFallback>
                          </Avatar>

                          <div className="flex-1 space-y-3">
                            <div className="flex items-start justify-between">
                              <div>
                                <h3 className="text-lg font-semibold text-white hover:text-yellow-400 transition-colors">
                                  {discussion.title}
                                </h3>
                                <div className="flex items-center gap-2 text-sm text-gray-400 mt-1">
                                  <span>by {discussion.author}</span>
                                  <span>•</span>
                                  <span>{discussion.timeAgo}</span>
                                  <Badge variant="outline" className="border-yellow-400 text-yellow-400 ml-2">
                                    {discussion.category}
                                  </Badge>
                                </div>
                              </div>
                            </div>

                            <p className="text-gray-300 line-clamp-2">{discussion.preview}</p>

                            <div className="flex items-center gap-6 text-sm text-gray-400">
                              <div className="flex items-center gap-1 hover:text-yellow-400 transition-colors cursor-pointer">
                                <Heart className="h-4 w-4" />
                                <span>{discussion.likes}</span>
                              </div>
                              <div className="flex items-center gap-1 hover:text-yellow-400 transition-colors cursor-pointer">
                                <MessageCircle className="h-4 w-4" />
                                <span>{discussion.replies} replies</span>
                              </div>
                              <div className="flex items-center gap-1 hover:text-yellow-400 transition-colors cursor-pointer">
                                <Share2 className="h-4 w-4" />
                                <span>Share</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <div className="text-center">
                  <Button className="bg-yellow-400 text-black hover:bg-yellow-500">Load More Discussions</Button>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </main>
  )
}
