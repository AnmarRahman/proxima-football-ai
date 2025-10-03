// HomePage.tsx
import { FeaturesSection } from "@/components/features-section"
import { Footer } from "@/components/footer"
import { Header } from "@/components/header"
import { HeroSection } from "@/components/hero-section"

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col">
      <div className="flex flex-col h-screen">
        <Header />
        <HeroSection />
      </div>
      <FeaturesSection />
      <Footer />
    </main>
  )
}
