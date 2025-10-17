import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { GitCompare, Search, Target } from "lucide-react"

export function FeaturesSection() {
  const features = [
    {
      icon: Target,
      title: "AI Career Prediction",
      description:
        "Analyze player profiles, performance stats, and lifestyle factors to predict future career paths with unprecedented accuracy.",
      badge: "Core Feature",
      href: "/predictions",
      available: true,
    },
    {
      icon: Search,
      title: "Player Similarity Finder",
      description:
        "Find the closest matches from past and present players with detailed similarity scores and style comparisons.",
      badge: "Coming Soon",
      href: "#",
      available: false,
    },
    {
      icon: GitCompare,
      title: "Player Comparison Tool",
      description:
        "Side-by-side player analysis with interactive charts, radar graphs, and FIFA-style visual comparisons.",
      badge: "Coming Soon",
      href: "#",
      available: false,
    },
  ]

  return (
    <section className="py-24 bg-[#060606]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">Powerful AI-Driven Features</h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto text-balance">
            Discover the comprehensive suite of tools that make Proxima Football AI the ultimate platform for football
            analytics and predictions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <Card
              key={index}
              className={`group hover:shadow-xl hover:shadow-primary/10 transition-all duration-300 border-border/50 bg-card/80 backdrop-blur-sm ${
                !feature.available ? 'opacity-75' : ''
              }`}
            >
              <CardHeader>
                <div className="flex items-center justify-between mb-4">
                  <feature.icon 
                    className={`h-10 w-10 group-hover:scale-110 transition-transform duration-300 ${
                      feature.available ? 'text-primary' : 'text-muted-foreground'
                    }`} 
                  />
                  <Badge 
                    variant="secondary" 
                    className={`border-primary/20 ${
                      feature.available 
                        ? 'bg-primary/10 text-primary' 
                        : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                    }`}
                  >
                    {feature.badge}
                  </Badge>
                </div>
                <CardTitle className={`text-xl group-hover:text-primary transition-colors duration-300 ${
                  !feature.available ? 'text-muted-foreground' : ''
                }`}>
                  {feature.title}
                </CardTitle>
                <CardDescription className="text-muted-foreground leading-relaxed">
                  {feature.description}
                  {!feature.available && (
                    <span className="block mt-2 text-sm text-yellow-500 font-medium">
                      This feature will be available soon!
                    </span>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  className={`w-full transition-all duration-300 ${
                    feature.available
                      ? 'border-primary/30 hover:bg-primary/10 hover:border-primary/50 hover:text-white bg-transparent'
                      : 'border-muted-foreground/30 bg-transparent cursor-not-allowed opacity-60'
                  }`}
                  asChild={feature.available}
                  disabled={!feature.available}
                >
                  {feature.available ? (
                    <a href={feature.href}>Explore Feature</a>
                  ) : (
                    <span>Coming Soon</span>
                  )}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
