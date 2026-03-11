"use client";

import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";

interface PlayerSearchProps {
  onPlayerSelect?: (player: any) => void;
}

interface PlayerOption {
  id: string;
  name: string;
  fallbackJson?: string;
}

const FALLBACK_PLAYER_OPTIONS: PlayerOption[] = [
  { id: "mbappe", name: "Kylian Mbappe", fallbackJson: "mbappe.json" },
  { id: "haaland", name: "Erling Haaland", fallbackJson: "haaland.json" },
  { id: "messi", name: "Lionel Messi", fallbackJson: "messi.json" },
  { id: "ronaldo", name: "Cristiano Ronaldo", fallbackJson: "ronaldo.json" },
  { id: "neymar", name: "Neymar Jr.", fallbackJson: "neymar.json" },
];

export function PlayerSearch({ onPlayerSelect }: PlayerSearchProps) {
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState("");
  const [playerOptions, setPlayerOptions] = useState<PlayerOption[]>(FALLBACK_PLAYER_OPTIONS);

  const loadingMessages = [
    "Adding up goals...",
    "Accounting for player behavior...",
    "Calculating stamina and speed...",
    "Checking injury history...",
    "Analyzing tactical moves...",
    "Projecting future highlights...",
  ];

  useEffect(() => {
    let isMounted = true;

    const loadPlayers = async () => {
      try {
        const response = await fetch("/api/players", { cache: "no-store" });
        if (!response.ok) {
          return;
        }

        const payload = await response.json();
        const players = Array.isArray(payload?.players) ? payload.players : [];

        if (isMounted && players.length > 0) {
          setPlayerOptions(
            players.map((p: any) => ({
              id: String(p.id),
              name: String(p.name),
            }))
          );
        }
      } catch {
        // Keep fallback options when API is unavailable.
      }
    };

    loadPlayers();

    return () => {
      isMounted = false;
    };
  }, []);

  const handlePlayerSelect = async () => {
    if (!selectedPlayerId) {
      return;
    }

    setLoading(true);

    let i = 0;
    const interval = setInterval(() => {
      setLoadingText(loadingMessages[i % loadingMessages.length]);
      i += 1;
    }, 1000);

    try {
      const playerInfo = playerOptions.find((p) => p.id === selectedPlayerId);

      const response = await fetch(`/api/predictions/${selectedPlayerId}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Prediction fetch failed (${response.status})`);
      }

      const payload = await response.json();
      const stats = Array.isArray(payload?.stats) ? payload.stats : [];
      const resolvedName = payload?.player?.name || playerInfo?.name || selectedPlayerId;

      if (onPlayerSelect) {
        onPlayerSelect({
          id: selectedPlayerId,
          name: resolvedName,
          stats,
          meta: payload?.meta || null,
          source: payload?.source || "unknown",
        });
      }
    } catch (err) {
      console.error("Error fetching player prediction:", err);

      // Last-resort static fallback for local dev.
      try {
        const playerInfo = playerOptions.find((p) => p.id === selectedPlayerId);
        const fallbackJson = playerInfo?.fallbackJson || `${selectedPlayerId}.json`;
        const localRes = await fetch(`/data/predictions/${fallbackJson}`);
        if (!localRes.ok) {
          throw new Error(`Fallback prediction missing (${localRes.status})`);
        }

        const localData = await localRes.json();
        if (onPlayerSelect) {
          onPlayerSelect({
            id: selectedPlayerId,
            name: playerInfo?.name || selectedPlayerId,
            stats: Array.isArray(localData) ? localData : [],
            source: "fallback",
          });
        }
      } catch (fallbackErr) {
        console.error("Fallback prediction failed:", fallbackErr);
      }
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
          {playerOptions.map((p) => (
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
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-lg font-semibold text-muted-foreground">{loadingText}</p>
        </div>
      )}
    </div>
  );
}
