"use client";

import { Button } from "@/components/ui/button";
import { useState } from "react";

interface PlayerSearchProps {
  onPlayerSelect?: (player: any) => void;
}

const PLAYER_OPTIONS = [
  { id: "mbappe", name: "Kylian Mbappé", json: "mbappe.json" },
  { id: "haaland", name: "Erling Haaland", json: "haaland.json" },
  { id: "messi", name: "Lionel Messi", json: "messi.json" },
  { id: "ronaldo", name: "Cristiano Ronaldo", json: "ronaldo.json" },
  { id: "neymar", name: "Neymar Jr.", json: "neymar.json" },
];

export function PlayerSearch({ onPlayerSelect }: PlayerSearchProps) {
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
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

    let i = 0;
    const interval = setInterval(() => {
      setLoadingText(loadingMessages[i % loadingMessages.length]);
      i++;
    }, 1000);

    try {
      const playerInfo = PLAYER_OPTIONS.find((p) => p.id === selectedPlayerId);

      if (!playerInfo) {
        // If for some reason the option is not found, stop and clear loading
        clearInterval(interval);
        setLoading(false);
        setLoadingText("");
        return;
      }

      const response = await fetch(`/data/predictions/${playerInfo.json}`);
      const data = await response.json();

      if (onPlayerSelect) {
        onPlayerSelect({ ...playerInfo, stats: data });
      }
    } catch (err) {
      console.error("Error fetching player data:", err);
    } finally {
      clearInterval(interval);
      setLoading(false);
      setLoadingText("");
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
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
      {loading && (
        <div className="flex flex-col justify-center items-center py-20">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-lg font-semibold text-muted-foreground">{loadingText}</p>
        </div>
      )}
    </div>
  );
}
