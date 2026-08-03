"use client";

import { Button } from "@/components/ui/button";
import { AIAnalysisLoader } from "@/components/ai-analysis-loader";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatPosition } from "@/lib/player-position";
import { cn } from "@/lib/utils";
import { Check, ChevronsUpDown } from "lucide-react";
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
  const [pickerOpen, setPickerOpen] = useState(false);

  const selectedPlayer = playerOptions.find((player) => player.id === selectedPlayerId);

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
    const loaderStartedAt = Date.now();
    try {
      const response = await fetch(`/api/predictions/${selectedPlayerId}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error || "Prediction is unavailable.");
      }
      const remainingLoaderTime = Math.max(0, 3200 - (Date.now() - loaderStartedAt));
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
        <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={pickerOpen}
              aria-label="Search for a player"
              className="min-h-11 flex-1 justify-between border-border bg-background px-3 font-normal hover:bg-background"
              disabled={loading || playersLoading}
            >
              {selectedPlayer ? (
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate font-medium">{selectedPlayer.name}</span>
                  {selectedPlayer.position ? (
                    <span className="hidden shrink-0 text-xs text-muted-foreground sm:inline">
                      {formatPosition(selectedPlayer.position)}
                    </span>
                  ) : null}
                </span>
              ) : (
                <span className="text-muted-foreground">
                  {playersLoading ? "Loading players..." : "Search players..."}
                </span>
              )}
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent
            align="start"
            className="w-[var(--radix-popover-trigger-width)] p-0"
          >
            <Command>
              <CommandInput placeholder="Search by player, country, or position..." />
              <CommandList>
                <CommandEmpty>No matching player found.</CommandEmpty>
                <CommandGroup heading={`${playerOptions.length} available players`}>
                  {playerOptions.map((player) => (
                    <CommandItem
                      key={player.id}
                      value={`${player.name} ${player.nationality || ""} ${player.position || ""}`}
                      onSelect={() => {
                        setSelectedPlayerId(player.id);
                        setPickerOpen(false);
                        setMessage(null);
                      }}
                      className="py-3"
                    >
                      <Check
                        className={cn(
                          "h-4 w-4 text-primary",
                          selectedPlayerId === player.id ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium">{player.name}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {[player.position ? formatPosition(player.position) : null, player.nationality]
                            .filter(Boolean)
                            .join(" / ")}
                        </span>
                      </span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
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
