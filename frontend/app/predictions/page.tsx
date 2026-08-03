"use client";

import { CareerPredictionDashboard } from "@/components/career-prediction-dashboard";
import { Header } from "@/components/header";
import { PlayerSearch } from "@/components/player-search";
import { useState } from "react";

export default function PredictionsPage() {
  const [selectedPlayer, setSelectedPlayer] = useState<any>(null);

  return (
    <main className="min-h-screen">
      <Header />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
            AI Next-Season <span className="text-primary">Forecast</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-balance">
            Explore validated domestic-league appearance and goal forecasts for the next season, with calibrated
            uncertainty ranges and transparent model limitations.
          </p>
        </div>
        <PlayerSearch onPlayerSelect={setSelectedPlayer} />
        {selectedPlayer && <CareerPredictionDashboard {...selectedPlayer} />}
      </div>
    </main>
  );
}
