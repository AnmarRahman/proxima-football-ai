"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bot, MessageCircle, X, Zap } from "lucide-react"
import { useState } from "react"

export function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false)

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
    <Card className="fixed bottom-6 right-6 w-80 h-[400px] bg-gray-900 border-gray-800 shadow-xl z-50 flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between p-4 bg-yellow-400 text-black flex-shrink-0">
        <CardTitle className="text-lg font-semibold">AI Football Assistant</CardTitle>
        <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)} className="text-black hover:bg-yellow-500">
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 p-6 flex flex-col items-center justify-center text-center space-y-6">
        {/* Coming Soon Content */}
        <div className="space-y-4">
          <div className="flex items-center justify-center">
            <div className="relative">
              <div className="w-16 h-16 bg-yellow-400/20 rounded-full flex items-center justify-center">
                <Bot className="h-8 w-8 text-yellow-400" />
              </div>
              <div className="absolute -top-1 -right-1 w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center">
                <Zap className="h-3 w-3 text-black" />
              </div>
            </div>
          </div>
          
          <div className="space-y-2">
            <h3 className="text-xl font-bold text-white">AI Chat Coming Soon!</h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              We're training our AI assistant to become the ultimate football expert. 
              Soon you'll be able to ask about players, tactics, predictions, and get 
              real-time football insights!
            </p>
          </div>
        </div>

        {/* Features Preview */}
        <div className="space-y-3 w-full">
          <div className="text-xs font-semibold text-yellow-400 uppercase tracking-wide">Coming Features</div>
          <div className="space-y-2">
            <div className="flex items-center space-x-3 text-sm text-gray-300">
              <div className="w-2 h-2 bg-yellow-400 rounded-full flex-shrink-0"></div>
              <span>Player analysis & comparisons</span>
            </div>
            <div className="flex items-center space-x-3 text-sm text-gray-300">
              <div className="w-2 h-2 bg-yellow-400 rounded-full flex-shrink-0"></div>
              <span>Tactical insights & formations</span>
            </div>
            <div className="flex items-center space-x-3 text-sm text-gray-300">
              <div className="w-2 h-2 bg-yellow-400 rounded-full flex-shrink-0"></div>
              <span>Transfer market predictions</span>
            </div>
            <div className="flex items-center space-x-3 text-sm text-gray-300">
              <div className="w-2 h-2 bg-yellow-400 rounded-full flex-shrink-0"></div>
              <span>Real-time match analysis</span>
            </div>
          </div>
        </div>

        {/* Status */}
        <div className="bg-yellow-400/10 border border-yellow-400/20 rounded-lg p-3 w-full">
          <div className="flex items-center justify-center space-x-2">
            <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
            <span className="text-xs text-yellow-400 font-medium">Currently in development</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}