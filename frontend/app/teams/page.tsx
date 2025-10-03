import { Header } from "@/components/header"
import { TeamAnalysisDashboard } from "@/components/team-analysis-dashboard"
import { TeamSelector } from "@/components/team-selector"

export default function TeamsPage() {
  return (
    <main className="min-h-screen">
      <Header />
      <div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
              Team <span className="text-primary">Analysis</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-balance">
              Comprehensive squad analysis with age breakdowns, peak performance windows, and 3-5 year future
              predictions. Discover your team's potential.
            </p>
          </div>
          <TeamSelector />
          <TeamAnalysisDashboard />
        </div>
      </div>
    </main>
  )
}
