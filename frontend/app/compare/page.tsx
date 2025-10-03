import { ComparisonDashboard } from "@/components/comparison-dashboard"
import { Header } from "@/components/header"
import { PlayerSelector } from "@/components/player-selector"

export default function ComparePage() {
  return (
    <main className="min-h-screen">
      <Header />
      <div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
              Player <span className="text-primary">Comparison</span> Tool
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-balance">
              Compare any two players side-by-side with detailed statistics, visual charts, and FIFA-style attribute
              breakdowns. Discover who comes out on top.
            </p>
          </div>
          <PlayerSelector />
          <ComparisonDashboard />
        </div>
      </div>
    </main>
  )
}
