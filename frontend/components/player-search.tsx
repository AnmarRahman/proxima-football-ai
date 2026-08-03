"use client";

import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";

interface PlayerSearchProps {
  onPlayerSelect?: (player: any) => void;
}

interface PlayerOption {
  id: string;
  name: string;
  nationality?: string | null;
  position?: string | null;
  predicted_season?: string | null;
}

export function PlayerSearch({ onPlayerSelect }: PlayerSearchProps) {
  const [selectedPlayerId, setSelectedPlayerId] = useState("");
  const [loading, setLoading] = useState(false);
  const [playersLoading, setPlayersLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [playerOptions, setPlayerOptions] = useState<PlayerOption[]>([]);

  useEffect(() => {
    let mounted = true;
    async function loadPlayers() {
      try {
        const response = await fetch("/api/players", { cache: "no-store" });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload?.error || "Could not load eligible players.");
        }
        if (mounted) {
          setPlayerOptions(Array.isArray(payload.players) ? payload.players : []);
          if (!payload.players?.length) {
            setMessage("No current Tier A predictions are available. Run the prediction workflow first.");
          }
        }
      } catch (error: any) {
        if (mounted) {
          setMessage(error?.message || "Could not load eligible players.");
        }
      } finally {
        if (mounted) setPlayersLoading(false);
      }
    }
    loadPlayers();
    return () => {
      mounted = false;
    };
  }, []);

  async function handlePlayerSelect() {
    if (!selectedPlayerId) return;
    setLoading(true);
    setMessage(null);
    onPlayerSelect?.(null);
    try {
      const response = await fetch(`/api/predictions/${selectedPlayerId}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error || "Prediction is unavailable.");
      }
      onPlayerSelect?.(payload);
    } catch (error: any) {
      setMessage(error?.message || "Prediction is unavailable right now.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-4xl rounded-2xl border border-border/60 bg-card/50 p-5 backdrop-blur-sm">
      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="sr-only" htmlFor="player-prediction-select">Player</label>
        <select
          id="player-prediction-select"
          className="min-h-11 flex-1 rounded-lg border border-border bg-background px-3 text-foreground outline-none focus:border-primary disabled:opacity-60"
          value={selectedPlayerId}
          onChange={(event) => setSelectedPlayerId(event.target.value)}
          disabled={loading || playersLoading}
        >
          <option value="">Select a player with a current forecast...</option>
          {playerOptions.map((player) => (
            <option key={player.id} value={player.id}>
              {player.name}{player.position ? ` / ${player.position}` : ""}
            </option>
          ))}
        </select>
        <Button
          className="min-h-11 px-6"
          onClick={handlePlayerSelect}
          disabled={loading || playersLoading || !selectedPlayerId}
        >
          {playersLoading ? "Loading..." : loading ? "Loading forecast..." : "View Forecast"}
        </Button>
      </div>
      {message ? <p className="mt-3 text-sm text-amber-300" role="status">{message}</p> : null}
      {!message && !playersLoading ? (
        <p className="mt-3 text-xs text-muted-foreground">
          Showing {playerOptions.length} active outfield player{playerOptions.length === 1 ? "" : "s"} with stored Tier A predictions.
        </p>
      ) : null}
    </section>
  );
}
