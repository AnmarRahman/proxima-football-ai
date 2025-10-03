"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bot, MessageCircle, Send, User, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"

interface Message {
  id: number
  text: string
  sender: "user" | "ai"
  timestamp: Date
}

export function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Hi! I'm your AI football assistant. Ask me anything about players, teams, predictions, or football analytics!",
      sender: "ai",
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = () => {
    if (!inputValue.trim()) return

    const userMessage: Message = {
      id: messages.length + 1,
      text: inputValue,
      sender: "user",
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")

    // Simulate AI response
    setTimeout(() => {
      const aiResponse: Message = {
        id: messages.length + 2,
        text: getAIResponse(inputValue),
        sender: "ai",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, aiResponse])
    }, 1000)
  }

  const getAIResponse = (userInput: string): string => {
    const input = userInput.toLowerCase()
    if (input.includes("messi") || input.includes("goat")) {
      return "Messi's World Cup victory in 2022 certainly strengthened his GOAT argument! His career stats show 800+ goals and 350+ assists. Would you like me to compare him with other legends?"
    }
    if (input.includes("prediction") || input.includes("predict")) {
      return "I can help with predictions! Try our Career Prediction tool to see detailed forecasts for any player's future performance, including goals, assists, and trophy probabilities."
    }
    if (input.includes("compare") || input.includes("vs")) {
      return "Player comparisons are my specialty! Use our Compare Players tool to see detailed side-by-side analysis with FIFA-style attributes and performance metrics."
    }
    if (input.includes("team") || input.includes("squad")) {
      return "Team analysis is fascinating! Our Team Analysis feature provides squad age distribution, position breakdowns, and 5-year performance projections. Which team interests you?"
    }
    if (input.includes("transfer") || input.includes("signing")) {
      return "Transfer analysis involves many factors - player fit, team needs, financial impact, and performance projections. I can help analyze any potential transfer scenario!"
    }
    return "That's an interesting question! I can help with player analysis, team predictions, transfer insights, and football statistics. What specific aspect would you like to explore?"
  }

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full bg-yellow-400 text-black hover:bg-yellow-500 shadow-lg z-50"
      >
        <MessageCircle className="h-6 w-6" />
      </Button>
    )
  }

  return (
    <Card className="fixed bottom-6 right-6 w-80 h-[500px] bg-gray-900 border-gray-800 shadow-xl z-50 flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between p-4 bg-yellow-400 text-black flex-shrink-0">
        <CardTitle className="text-lg font-semibold">AI Football Assistant</CardTitle>
        <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)} className="text-black hover:bg-yellow-500">
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 p-0 flex flex-col overflow-hidden">
        {/* Scrollable messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${message.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {message.sender === "ai" && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-yellow-400 text-black">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}

              <div
                className={`max-w-[70%] p-3 rounded-lg text-sm break-words whitespace-pre-wrap ${message.sender === "user" ? "bg-yellow-400 text-black" : "bg-gray-800 text-white"
                  }`}
              >
                {message.text}
              </div>


              {message.sender === "user" && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-gray-700 text-white">
                    <User className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}
          {/* Dummy div to scroll to */}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-800">
          <div className="flex gap-2">
            <textarea
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value)
                e.target.style.height = "auto" // reset height
                e.target.style.height = e.target.scrollHeight + "px" // set height based on content
              }}
              placeholder="ASK PROXIMA AI"
              className="flex-1 bg-gray-800 border-gray-700 text-white rounded-md p-2 resize-none overflow-hidden"
              rows={1}
              onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && handleSendMessage()}
            />
            <Button onClick={handleSendMessage} className="bg-yellow-400 text-black hover:bg-yellow-500">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
