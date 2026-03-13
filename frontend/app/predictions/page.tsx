"use client";

import { CareerPredictionDashboard } from "@/components/career-prediction-dashboard";
import { Header } from "@/components/header";
import { PlayerSearch } from "@/components/player-search";
import { useMemo, useState } from "react";

type SelectedPlayer = {
  id: string;
  name: string;
  stats?: Array<Record<string, unknown>>;
  source?: string;
  meta?: Record<string, unknown> | null;
} | null;

export default function PredictionsPage() {
  const [selectedPlayer, setSelectedPlayer] = useState<SelectedPlayer>(null);

  const hasStats = useMemo(() => {
    return Boolean(selectedPlayer && Array.isArray(selectedPlayer.stats) && selectedPlayer.stats.length > 0);
  }, [selectedPlayer]);

  return (
    <main className="min-h-screen">
      <Header />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
            AI Career <span className="text-primary">Prediction</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-balance">
            Discover what the future holds for football&apos;s biggest stars. Our AI analyzes performance data, injury
            history, and career patterns to predict player trajectories.
          </p>
        </div>

        <PlayerSearch onPlayerSelect={setSelectedPlayer} />

        {selectedPlayer && hasStats ? <CareerPredictionDashboard player={selectedPlayer as any} /> : null}

        {selectedPlayer && !hasStats ? (
          <div className="mx-auto mt-8 max-w-3xl rounded-xl border border-[#2A2A2A] bg-[#0B0B0B] p-6 text-center">
            <h2 className="text-xl font-semibold text-[#D4AF37]">No Prediction Available</h2>
            <p className="mt-2 text-sm text-gray-300">
              We don&apos;t have enough prediction rows yet for {selectedPlayer.name}. Try another player or run the latest
              prediction pipeline from Admin.
            </p>
          </div>
        ) : null}
      </div>
    </main>
  );
}
