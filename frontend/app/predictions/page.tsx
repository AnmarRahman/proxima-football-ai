"use client";

import { CareerPredictionDashboard } from "@/components/career-prediction-dashboard";
import { Header } from "@/components/header";
import { PlayerSearch } from "@/components/player-search";
import { useState } from "react";

export default function PredictionsPage() {
  // Accept anything, as PlayerSearch gives full details and stats
  const [selectedPlayer, setSelectedPlayer] = useState<any>(null);

  return (
    <main className="min-h-screen">
      <Header />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
            AI Career <span className="text-primary">Prediction</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-balance">
            Discover what the future holds for football's biggest stars. Our AI analyzes performance data, injury
            history, and career patterns to predict player trajectories.
          </p>
        </div>
        {/* Pass the callback directly; PlayerSearch sends back complete { ...player, stats } object */}
        <PlayerSearch onPlayerSelect={setSelectedPlayer} />
        {/* Only show CareerPredictionDashboard if selectedPlayer is not null.
            The dashboard accesses all details (name, id, stats, etc.) from player prop. */}
        {selectedPlayer && <CareerPredictionDashboard player={selectedPlayer} />}
      </div>
    </main>
  );
}
