// HeroSection.tsx
import { Button } from "@/components/ui/button"
import { ArrowRight, Brain, TrendingUp, Users } from "lucide-react"

export function HeroSection() {
  return (
    <section className="relative flex-1 flex flex-col justify-center overflow-hidden py-40">
      {/* Background image */}
      <div
        className="absolute inset-0 bg-cover bg-bottom"
        style={{ backgroundImage: "url('/hero.png')" }}
      />
      {/* Dark overlay */}
      <div className="absolute inset-0 bg-black/75" />

      {/* Floating circles */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-1/4 left-1/4 w-32 h-32 border border-primary/30 rounded-full animate-float" />
        <div
          className="absolute top-3/4 right-1/4 w-24 h-24 border border-primary/20 rounded-full animate-float"
          style={{ animationDelay: "1s" }}
        />
        <div
          className="absolute top-1/2 left-1/2 w-16 h-16 border border-primary/40 rounded-full animate-float"
          style={{ animationDelay: "2s" }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <span className="inline-block px-4 py-2 bg-primary/10 text-primary rounded-full text-sm font-medium border border-primary/20 mb-8">
          Powered by Advanced AI
        </span>

        <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-balance mb-6">
          <span className="text-foreground">Predicting the</span>
          <br />
          <span className="text-primary animate-glow">Beautiful Game</span>
        </h1>

        <p className="text-sm md:text-lg text-muted-foreground text-balance mb-4 max-w-3xl mx-auto leading-relaxed">
          Harness the power of artificial intelligence to predict player careers, analyze performance, and discover the
          future stars of football.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-8">
          <Button size="lg" className="bg-primary uppercase text-primary-foreground hover:bg-primary/90 text-lg px-8 py-4 group">
            Explore AI Predictions
            <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="text-lg uppercase px-8 py-4 border-primary/80 bg-[#090B0D]! hover:bg-black! hover:text-white"
          >
            Watch Demo
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div className="flex flex-col items-center p-6 bg-card/50 rounded-xl border border-border/50 backdrop-blur-sm">
            <Brain className="h-12 w-12 text-primary mb-2" />
            <h3 className="text-lg font-semibold mb-1">AI Career Prediction</h3>
            <p className="text-sm text-muted-foreground text-center">
              Advanced algorithms predict player trajectories and career milestones
            </p>
          </div>
          <div className="flex flex-col items-center p-6 bg-card/50 rounded-xl border border-border/50 backdrop-blur-sm">
            <TrendingUp className="h-12 w-12 text-primary mb-2" />
            <h3 className="text-lg font-semibold mb-1">Performance Analytics</h3>
            <p className="text-sm text-muted-foreground text-center">
              Deep statistical analysis and similarity matching with historical data
            </p>
          </div>
          <div className="flex flex-col items-center p-6 bg-card/50 rounded-xl border border-border/50 backdrop-blur-sm">
            <Users className="h-12 w-12 text-primary mb-2" />
            <h3 className="text-lg font-semibold mb-1">Team Insights</h3>
            <p className="text-sm text-muted-foreground text-center">
              Comprehensive squad analysis and future performance predictions
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
