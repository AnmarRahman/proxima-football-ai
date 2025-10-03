import { Header } from "@/components/header"
import { SimilarityResults } from "@/components/similarity-results"
import { SimilaritySearch } from "@/components/similarity-search"

export default function SimilarityPage() {
  return (
    <main className="min-h-screen">
      <Header />
      <div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
              Player <span className="text-primary">Similarity</span> Finder
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-balance">
              Discover players with similar playing styles, attributes, and career patterns. Our AI compares thousands
              of data points to find the closest matches from past and present.
            </p>
          </div>
          <SimilaritySearch />
          <SimilarityResults />
        </div>
      </div>
    </main>
  )
}
