"use client";

import { Button } from "@/components/ui/button";
import { AIAnalysisLoader } from "@/components/ai-analysis-loader";
import { formatPosition } from "@/lib/player-position";
import { Check, ChevronDown, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

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
  const [pickerOpen, setPickerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const pickerRef = useRef<HTMLDivElement>(null);

  const selectedPlayer = playerOptions.find((player) => player.id === selectedPlayerId);
  const filteredPlayers = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return playerOptions;
    return playerOptions.filter((player) =>
      [player.name, player.nationality, player.position && formatPosition(player.position)]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term))
    );
  }, [playerOptions, query]);

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

  useEffect(() => {
    function closePicker(event: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setPickerOpen(false);
      }
    }
    document.addEventListener("mousedown", closePicker);
    return () => document.removeEventListener("mousedown", closePicker);
  }, []);

  async function handlePlayerSelect() {
    if (!selectedPlayerId) return;
    setLoading(true);
    setMessage(null);
    onPlayerSelect?.(null);
    const loaderStartedAt = Date.now();
    try {
      const response = await fetch(`/api/predictions/${selectedPlayerId}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error || "Prediction is unavailable.");
      }
      const remainingLoaderTime = Math.max(0, 9200 - (Date.now() - loaderStartedAt));
      if (remainingLoaderTime) {
        await new Promise((resolve) => window.setTimeout(resolve, remainingLoaderTime));
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
        <div ref={pickerRef} className="relative flex-1">
          <div className="flex min-h-11 items-center rounded-md border border-border bg-background px-3 focus-within:border-primary/70 focus-within:ring-2 focus-within:ring-primary/20">
            <Search className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              type="text"
              role="combobox"
              aria-expanded={pickerOpen}
              aria-controls="player-search-results"
              aria-label="Search for a player"
              value={query}
              placeholder={playersLoading ? "Loading players..." : "Search by player, country, or position..."}
              disabled={loading || playersLoading}
              onFocus={() => setPickerOpen(true)}
              onClick={() => setPickerOpen(true)}
              onChange={(event) => {
                setQuery(event.target.value);
                setSelectedPlayerId("");
                setPickerOpen(true);
                setMessage(null);
              }}
              className="h-10 min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60"
            />
            <button
              type="button"
              aria-label="Toggle player list"
              disabled={loading || playersLoading}
              onClick={() => setPickerOpen((open) => !open)}
              className="ml-2 rounded p-1 text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
            >
              <ChevronDown className={`h-4 w-4 transition-transform ${pickerOpen ? "rotate-180" : ""}`} />
            </button>
          </div>

          {pickerOpen && !playersLoading ? (
            <div
              id="player-search-results"
              role="listbox"
              className="absolute z-[100] mt-2 max-h-80 w-full overflow-y-auto rounded-lg border border-border bg-popover p-1 text-popover-foreground shadow-2xl"
            >
              <p className="px-3 py-2 text-xs font-medium text-muted-foreground">
                {filteredPlayers.length} player{filteredPlayers.length === 1 ? "" : "s"}
              </p>
              {filteredPlayers.length ? filteredPlayers.map((player) => (
                <button
                  key={player.id}
                  type="button"
                  role="option"
                  aria-selected={selectedPlayerId === player.id}
                  onClick={() => {
                    setSelectedPlayerId(player.id);
                    setQuery(player.name);
                    setPickerOpen(false);
                    setMessage(null);
                  }}
                  className="flex w-full items-center gap-3 rounded-md px-3 py-3 text-left transition-colors hover:bg-accent focus:bg-accent focus:outline-none"
                >
                  <Check className={`h-4 w-4 shrink-0 text-primary ${selectedPlayerId === player.id ? "opacity-100" : "opacity-0"}`} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{player.name}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {[player.position ? formatPosition(player.position) : null, player.nationality]
                        .filter(Boolean)
                        .join(" / ")}
                    </span>
                  </span>
                </button>
              )) : (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">No matching player found.</p>
              )}
            </div>
          ) : null}
        </div>
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
      {loading ? (
        <AIAnalysisLoader
          playerName={selectedPlayer?.name || "player"}
        />
      ) : null}
    </section>
  );
}
