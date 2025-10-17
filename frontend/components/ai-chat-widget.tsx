"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bot, MessageCircle, X, Zap } from "lucide-react"
import { useEffect, useState } from "react"

export function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [viewportBottomPadding, setViewportBottomPadding] = useState(24) // dynamic safe-area padding

  // Adjust for mobile safe-area insets so the widget never gets cut off
  useEffect(() => {
    const computePadding = () => {
      const envSafe = parseInt(getComputedStyle(document.documentElement).getPropertyValue('env(safe-area-inset-bottom)').replace('px',''))
      const constantSafe = parseInt(getComputedStyle(document.documentElement).getPropertyValue('constant(safe-area-inset-bottom)').replace('px',''))
      const safe = Math.max(envSafe || 0, constantSafe || 0)
      setViewportBottomPadding(24 + safe)
    }
    computePadding()
    window.addEventListener('resize', computePadding)
    return () => window.removeEventListener('resize', computePadding)
  }, [])

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        className="fixed z-[100] h-14 w-14 rounded-full bg-yellow-400 text-black hover:bg-yellow-500 shadow-lg"
        style={{ right: 24, bottom: viewportBottomPadding }}
      >
        <MessageCircle className="h-6 w-6" />
      </Button>
    )
  }

  return (
    <Card
      className="fixed z-[100] w-[90vw] max-w-[360px] bg-gray-900 border-gray-800 shadow-xl flex flex-col"
      style={{
        right: 24,
        bottom: viewportBottomPadding,
        // Ensure the full widget is visible above footer and within viewport
        maxHeight: 'min(80vh, 640px)',
      }}
    >
      <CardHeader className="flex flex-row items-center justify-between p-4 bg-yellow-400 text-black flex-shrink-0 sticky top-0">
        <CardTitle className="text-lg font-semibold">AI Football Assistant</CardTitle>
        <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)} className="text-black hover:bg-yellow-500">
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent className="p-0">
        <div className="p-6 text-center space-y-6 overflow-y-auto" style={{ maxHeight: 'calc(min(80vh, 640px) - 64px)' }}>
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

            <div className="space-y-2 px-2">
              <h3 className="text-xl font-bold text-white">AI Chat Coming Soon!</h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                We're training our AI assistant to become the ultimate football expert. Soon you'll be able to ask about players, tactics, predictions, and get real-time football insights!
              </p>
            </div>
          </div>

          <div className="space-y-3 w-full text-left">
            <div className="text-xs font-semibold text-yellow-400 uppercase tracking-wide">Coming Features</div>
            <ul className="space-y-2">
              <li className="flex items-center space-x-3 text-sm text-gray-300"><span className="w-2 h-2 bg-yellow-400 rounded-full"></span><span>Player analysis & comparisons</span></li>
              <li className="flex items-center space-x-3 text-sm text-gray-300"><span className="w-2 h-2 bg-yellow-400 rounded-full"></span><span>Tactical insights & formations</span></li>
              <li className="flex items-center space-x-3 text-sm text-gray-300"><span className="w-2 h-2 bg-yellow-400 rounded-full"></span><span>Transfer market predictions</span></li>
              <li className="flex items-center space-x-3 text-sm text-gray-300"><span className="w-2 h-2 bg-yellow-400 rounded-full"></span><span>Real-time match analysis</span></li>
            </ul>
          </div>

          <div className="bg-yellow-400/10 border border-yellow-400/20 rounded-lg p-3 w-full">
            <div className="flex items-center justify-center space-x-2">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
              <span className="text-xs text-yellow-400 font-medium">Currently in development</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
