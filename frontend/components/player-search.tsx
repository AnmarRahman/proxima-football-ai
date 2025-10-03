"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useState } from "react";

interface PlayerSearchProps {
  onPlayerSelect?: (player: any) => void;
}

const PLAYER_OPTIONS = [
  { id: "mbappe", name: "Kylian Mbappé" },
  { id: "haaland", name: "Erling Haaland" },
  { id: "messi", name: "Lionel Messi" },
  { id: "ronaldo", name: "Cristiano Ronaldo" },
  { id: "neymar", name: "Neymar Jr." },
];

export function PlayerSearch({ onPlayerSelect }: PlayerSearchProps) {
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
  const [prediction, setPrediction] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState("");

  const loadingMessages = [
    "Adding up goals ⚽...",
    "Accounting player's behaviour 🤔...",
    "Calculating stamina and speed 💨...",
    "Checking injury history 🩹...",
    "Analyzing tactical moves 📊...",
    "Projecting future highlights 🌟..."
  ];

  const handlePlayerSelect = async () => {
    if (!selectedPlayerId) return;
    setLoading(true);

    // Start rotating loading messages
    let i = 0;
    const interval = setInterval(() => {
      setLoadingText(loadingMessages[i % loadingMessages.length]);
      i++;
    }, 1000);

    try {
      const response = await fetch(`http://127.0.0.1:8000/predict?player_id=${selectedPlayerId}`);
      const data = await response.json();
      console.log(data)

      // The backend returns the JSON with all stats directly
      setPrediction(data.predicted_next_season);

      // Notify parent if needed
      if (onPlayerSelect) {
        const playerInfo = PLAYER_OPTIONS.find((p) => p.id === selectedPlayerId);
        onPlayerSelect(playerInfo);
      }
    } catch (err) {
      console.error("Error fetching prediction:", err);
    } finally {
      clearInterval(interval);
      setLoading(false);
      setLoadingText("");
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      {/* Player selection */}
      <div className="mb-6 flex gap-2 flex-wrap items-center">
        <select
          className="border border-border rounded px-2 py-1 bg-background text-foreground"
          value={selectedPlayerId}
          onChange={(e) => setSelectedPlayerId(e.target.value)}
        >
          <option value="">Select a player...</option>
          {PLAYER_OPTIONS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <Button onClick={handlePlayerSelect} disabled={loading || !selectedPlayerId}>
          {loading ? "Predicting..." : "Predict Career"}
        </Button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col justify-center items-center py-20">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-lg font-semibold text-muted-foreground">{loadingText}</p>
        </div>
      )}

      {/* Predicted Stats */}
      {!loading && prediction && (
        <Card className="bg-card/80 border border-border/20 mt-6">
          <CardContent className="flex flex-col gap-2">
            <h3 className="font-semibold text-lg">
              {PLAYER_OPTIONS.find((p) => p.id === selectedPlayerId)?.name} - Predicted Next Season Stats
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm text-muted-foreground">
              {Object.entries(prediction).map(([key, value]) => (
                <span key={key}>
                  {key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (c) => c.toUpperCase())}: {Math.round(Number(value) * 100) / 100}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
