"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type SessionResponse = {
  authenticated: boolean;
  configured: boolean;
  provider?: string;
};

type UploadResult = {
  file: string;
  playerId?: string;
  seasonsImported?: number;
  importKind?: "tier-a" | "detailed";
  error?: string;
};

type UploadResponse = {
  ok: boolean;
  provider?: string;
  overAgeThreshold: number;
  totals: {
    filesReceived: number;
    imported: number;
    failed: number;
  };
  successes: UploadResult[];
  failures: UploadResult[];
  error?: string;
};

type PlayerSeason = {
  season: number;
  team_id: string | null;
  league_id: string | null;
  appearances: number;
  goals: number;
  assists: number;
  minutes: number;
  position: string | null;
  rating: number | null;
  xg: number | null;
  xa: number | null;
  key_passes: number | null;
  successful_dribbles: number | null;
  duels_won: number | null;
  shots_per_game: number | null;
  tackles_per_game: number | null;
  fouls_drawn: number | null;
  raw_json: unknown;
};

type AdminPlayer = {
  id: string;
  name: string;
  nationality: string | null;
  birth_date: string | null;
  is_retired: boolean;
  over_35: boolean;
  retired_since: string | null;
  season_count: number;
  career_totals: {
    appearances: number;
    goals: number;
    assists: number;
    minutes: number;
  };
  latest_season: PlayerSeason | null;
  seasons: PlayerSeason[];
};

type DatabaseResponse = {
  players: AdminPlayer[];
  totals: {
    players: number;
    seasons: number;
  };
  error?: string;
};

type PredictionStatus = {
  approvedModels: Array<{
    version: string;
    data_version: string;
    approved: boolean;
    trained_at: string | null;
  }>;
  recentRuns: Array<{
    id: string;
    status: string;
    model_version: string;
    started_at: string;
    ended_at: string | null;
    predicted_count: number;
    rejected_count: number;
    error_message: string | null;
  }>;
  predictionCount: number;
};

type SeasonEditorMode = "manual" | "json";

type SeasonManualDraft = {
  season: string;
  team_id: string;
  league_id: string;
  position: string;
  appearances: string;
  goals: string;
  assists: string;
  minutes: string;
  rating: string;
  xg: string;
  xa: string;
  key_passes: string;
  successful_dribbles: string;
  duels_won: string;
  shots_per_game: string;
  tackles_per_game: string;
  fouls_drawn: string;
};

const MANUAL_FIELDS: Array<{ key: keyof SeasonManualDraft; label: string; required?: boolean }> = [
  { key: "season", label: "Season", required: true },
  { key: "team_id", label: "Team ID", required: true },
  { key: "league_id", label: "League ID" },
  { key: "position", label: "Position" },
  { key: "appearances", label: "Appearances" },
  { key: "goals", label: "Goals" },
  { key: "assists", label: "Assists" },
  { key: "minutes", label: "Minutes" },
  { key: "rating", label: "Rating" },
  { key: "xg", label: "xG" },
  { key: "xa", label: "xA" },
  { key: "key_passes", label: "Key Passes" },
  { key: "successful_dribbles", label: "Successful Dribbles" },
  { key: "duels_won", label: "Duels Won" },
  { key: "shots_per_game", label: "Shots per Game" },
  { key: "tackles_per_game", label: "Tackles per Game" },
  { key: "fouls_drawn", label: "Fouls Drawn" },
];

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asObjectArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((entry) => entry && typeof entry === "object" && !Array.isArray(entry)) as Record<
    string,
    unknown
  >[];
}

function normalizeId(value: string): string {
  return value.trim().toLowerCase();
}

function toInputString(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function toNullableInt(value: string): number | null {
  const clean = value.trim();
  if (!clean) {
    return null;
  }
  const parsed = Number(clean);
  if (!Number.isFinite(parsed)) {
    throw new Error(`Invalid number: ${value}`);
  }
  return Math.trunc(parsed);
}

function toNullableFloat(value: string): number | null {
  const clean = value.trim();
  if (!clean) {
    return null;
  }
  const parsed = Number(clean);
  if (!Number.isFinite(parsed)) {
    throw new Error(`Invalid number: ${value}`);
  }
  return parsed;
}

function safeJsonStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "{}";
  }
}

function emptySeasonDoc(): Record<string, unknown> {
  return {
    season: "",
    team_id: "",
    league_id: "unknown",
    appearances: null,
    goals: null,
    assists: null,
    minutes: null,
    position: null,
    rating: null,
    xG: null,
    xA: null,
    key_passes: null,
    successful_dribbles: null,
    duels_won: null,
    shots_per_game: null,
    tackles_per_game: null,
    fouls_drawn: null,
    physical_metrics: {},
    tactical_data: {},
    national_team_stats: [],
    injuries: [],
    transfer_history: [],
  };
}

function seasonDocFromRow(row: PlayerSeason): Record<string, unknown> {
  const raw = asRecord(row.raw_json);
  if (Object.keys(raw).length) {
    return {
      ...raw,
      season: Number(raw.season ?? row.season),
      team_id: String(raw.team_id ?? row.team_id ?? "").trim().toLowerCase(),
      league_id: String(raw.league_id ?? row.league_id ?? "unknown").trim().toLowerCase() || "unknown",
      national_team_stats: asObjectArray(raw.national_team_stats),
      injuries: asObjectArray(raw.injuries),
      transfer_history: asObjectArray(raw.transfer_history),
      physical_metrics: asRecord(raw.physical_metrics),
      tactical_data: asRecord(raw.tactical_data),
    };
  }

  return {
    season: row.season,
    team_id: row.team_id || "",
    league_id: row.league_id || "unknown",
    appearances: row.appearances,
    goals: row.goals,
    assists: row.assists,
    minutes: row.minutes,
    position: row.position,
    rating: row.rating,
    xG: row.xg,
    xA: row.xa,
    key_passes: row.key_passes,
    successful_dribbles: row.successful_dribbles,
    duels_won: row.duels_won,
    shots_per_game: row.shots_per_game,
    tackles_per_game: row.tackles_per_game,
    fouls_drawn: row.fouls_drawn,
    physical_metrics: {},
    tactical_data: {},
    national_team_stats: [],
    injuries: [],
    transfer_history: [],
  };
}

function draftFromSeasonDoc(doc: Record<string, unknown>): SeasonManualDraft {
  return {
    season: toInputString(doc.season),
    team_id: toInputString(doc.team_id),
    league_id: toInputString(doc.league_id || "unknown"),
    position: toInputString(doc.position),
    appearances: toInputString(doc.appearances),
    goals: toInputString(doc.goals),
    assists: toInputString(doc.assists),
    minutes: toInputString(doc.minutes),
    rating: toInputString(doc.rating),
    xg: toInputString(doc.xG ?? doc.xg),
    xa: toInputString(doc.xA ?? doc.xa),
    key_passes: toInputString(doc.key_passes),
    successful_dribbles: toInputString(doc.successful_dribbles),
    duels_won: toInputString(doc.duels_won),
    shots_per_game: toInputString(doc.shots_per_game),
    tackles_per_game: toInputString(doc.tackles_per_game),
    fouls_drawn: toInputString(doc.fouls_drawn),
  };
}

function seasonDocFromDraft(
  draft: SeasonManualDraft,
  base: Record<string, unknown>
): Record<string, unknown> {
  const seasonYear = Number(draft.season.trim());
  if (!Number.isFinite(seasonYear) || seasonYear < 1900 || seasonYear > 2200) {
    throw new Error("Season year must be a valid year.");
  }

  const teamId = normalizeId(draft.team_id);
  if (!teamId) {
    throw new Error("Team ID is required.");
  }

  const leagueId = normalizeId(draft.league_id || "unknown") || "unknown";

  return {
    ...base,
    season: Math.trunc(seasonYear),
    team_id: teamId,
    league_id: leagueId,
    position: draft.position.trim() || null,
    appearances: toNullableInt(draft.appearances),
    goals: toNullableInt(draft.goals),
    assists: toNullableInt(draft.assists),
    minutes: toNullableInt(draft.minutes),
    rating: toNullableFloat(draft.rating),
    xG: toNullableFloat(draft.xg),
    xA: toNullableFloat(draft.xa),
    key_passes: toNullableInt(draft.key_passes),
    successful_dribbles: toNullableInt(draft.successful_dribbles),
    duels_won: toNullableInt(draft.duels_won),
    shots_per_game: toNullableFloat(draft.shots_per_game),
    tackles_per_game: toNullableFloat(draft.tackles_per_game),
    fouls_drawn: toNullableInt(draft.fouls_drawn),
    physical_metrics: asRecord(base.physical_metrics),
    tactical_data: asRecord(base.tactical_data),
    national_team_stats: asObjectArray(base.national_team_stats),
    injuries: asObjectArray(base.injuries),
    transfer_history: asObjectArray(base.transfer_history),
  };
}

export default function AdminPage() {
  const [loadingSession, setLoadingSession] = useState(true);
  const [configured, setConfigured] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [provider, setProvider] = useState("postgres");

  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

  const [dbLoading, setDbLoading] = useState(false);
  const [dbError, setDbError] = useState<string | null>(null);
  const [dbPlayers, setDbPlayers] = useState<AdminPlayer[]>([]);
  const [dbTotals, setDbTotals] = useState({ players: 0, seasons: 0 });

  const [editingPlayerId, setEditingPlayerId] = useState<string | null>(null);
  const [editingPlayerName, setEditingPlayerName] = useState("");
  const [editingSeasonKey, setEditingSeasonKey] = useState("new");
  const [editorMode, setEditorMode] = useState<SeasonEditorMode>("manual");
  const [baseSeasonDoc, setBaseSeasonDoc] = useState<Record<string, unknown>>(emptySeasonDoc());
  const [manualDraft, setManualDraft] = useState<SeasonManualDraft>(draftFromSeasonDoc(emptySeasonDoc()));
  const [seasonJson, setSeasonJson] = useState(safeJsonStringify(emptySeasonDoc()));
  const [savingSeason, setSavingSeason] = useState(false);
  const [seasonSaveError, setSeasonSaveError] = useState<string | null>(null);
  const [seasonSaveMessage, setSeasonSaveMessage] = useState<string | null>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [overAgeThreshold, setOverAgeThreshold] = useState("35");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [triggering, setTriggering] = useState(false);
  const [triggerMessage, setTriggerMessage] = useState<string | null>(null);
  const [triggerError, setTriggerError] = useState<string | null>(null);
  const [predictionStatus, setPredictionStatus] = useState<PredictionStatus | null>(null);

  const selectedFileLabel = useMemo(() => {
    if (!files.length) {
      return "No files selected";
    }
    if (files.length === 1) {
      return files[0].name;
    }
    return `${files.length} files selected`;
  }, [files]);

  async function refreshSession() {
    setLoadingSession(true);
    try {
      const res = await fetch("/api/admin/session", { cache: "no-store" });
      const data = (await res.json()) as SessionResponse;
      setConfigured(Boolean(data.configured));
      setAuthenticated(Boolean(data.authenticated));
      setProvider(String(data.provider || "postgres"));
    } catch {
      setConfigured(false);
      setAuthenticated(false);
      setProvider("unknown");
    } finally {
      setLoadingSession(false);
    }
  }

  async function loadDatabase() {
    setDbLoading(true);
    setDbError(null);

    try {
      const res = await fetch("/api/admin/database", { cache: "no-store" });
      const data = (await res.json()) as DatabaseResponse;

      if (res.status === 401) {
        setAuthenticated(false);
        setDbError("Session expired. Log in again.");
        return;
      }

      if (!res.ok) {
        setDbError(data?.error || "Failed to load database data.");
        return;
      }

      setDbPlayers(Array.isArray(data.players) ? data.players : []);
      setDbTotals({
        players: Number(data?.totals?.players || 0),
        seasons: Number(data?.totals?.seasons || 0),
      });
    } catch {
      setDbError("Failed to load database data due to a network error.");
    } finally {
      setDbLoading(false);
    }
  }

  async function loadPredictionStatus() {
    try {
      const response = await fetch("/api/admin/prediction-status", { cache: "no-store" });
      if (!response.ok) return;
      setPredictionStatus((await response.json()) as PredictionStatus);
    } catch {
      setPredictionStatus(null);
    }
  }

  useEffect(() => {
    refreshSession();
  }, []);

  useEffect(() => {
    if (!authenticated) {
      setDbPlayers([]);
      setDbTotals({ players: 0, seasons: 0 });
      return;
    }

    loadDatabase();
    loadPredictionStatus();
  }, [authenticated]);

  useEffect(() => {
    if (!editingPlayerId) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !savingSeason) {
        cancelSeasonEditor();
      }
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [editingPlayerId, savingSeason]);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setLoginError(null);
    setLoggingIn(true);

    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setLoginError(err?.error || "Login failed.");
        return;
      }

      setPassword("");
      await refreshSession();
    } catch {
      setLoginError("Login failed due to a network error.");
    } finally {
      setLoggingIn(false);
    }
  }

  async function handleLogout() {
    await fetch("/api/admin/logout", { method: "POST" });
    setAuthenticated(false);
    setUploadResult(null);
    setTriggerMessage(null);
    setDbPlayers([]);
    setDbTotals({ players: 0, seasons: 0 });
  }
  function startAddSeason(playerId: string, playerName: string) {
    const doc = emptySeasonDoc();
    setEditingPlayerId(playerId);
    setEditingPlayerName(playerName);
    setEditingSeasonKey("new");
    setEditorMode("manual");
    setBaseSeasonDoc(doc);
    setManualDraft(draftFromSeasonDoc(doc));
    setSeasonJson(safeJsonStringify(doc));
    setSeasonSaveError(null);
    setSeasonSaveMessage(null);
  }

  function startEditSeason(playerId: string, playerName: string, season: PlayerSeason) {
    const doc = seasonDocFromRow(season);
    setEditingPlayerId(playerId);
    setEditingPlayerName(playerName);
    setEditingSeasonKey(`${season.season}-${season.team_id || "none"}-${season.league_id || "unknown"}`);
    setEditorMode("manual");
    setBaseSeasonDoc(doc);
    setManualDraft(draftFromSeasonDoc(doc));
    setSeasonJson(safeJsonStringify(doc));
    setSeasonSaveError(null);
    setSeasonSaveMessage(null);
  }

  function cancelSeasonEditor() {
    setEditingPlayerId(null);
    setEditingPlayerName("");
    setEditingSeasonKey("new");
    setSeasonSaveError(null);
    setSeasonSaveMessage(null);
  }

  function setManualField(key: keyof SeasonManualDraft, value: string) {
    setManualDraft((prev) => ({ ...prev, [key]: value }));
    setSeasonSaveError(null);
    setSeasonSaveMessage(null);
  }

  function handleEditorModeChange(nextMode: SeasonEditorMode) {
    if (nextMode === editorMode) {
      return;
    }

    setSeasonSaveError(null);
    setSeasonSaveMessage(null);

    if (nextMode === "json") {
      try {
        const doc = seasonDocFromDraft(manualDraft, baseSeasonDoc);
        setSeasonJson(safeJsonStringify(doc));
      } catch {
        setSeasonJson(safeJsonStringify(baseSeasonDoc));
      }
    } else {
      try {
        const parsed = JSON.parse(seasonJson);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          const doc = parsed as Record<string, unknown>;
          setBaseSeasonDoc(doc);
          setManualDraft(draftFromSeasonDoc(doc));
        }
      } catch {
        // keep current draft
      }
    }

    setEditorMode(nextMode);
  }

  async function handleSaveSeason() {
    if (!editingPlayerId) {
      return;
    }

    setSavingSeason(true);
    setSeasonSaveError(null);
    setSeasonSaveMessage(null);

    let payload: Record<string, unknown>;

    try {
      if (editorMode === "manual") {
        const doc = seasonDocFromDraft(manualDraft, baseSeasonDoc);
        setBaseSeasonDoc(doc);
        setSeasonJson(safeJsonStringify(doc));
        payload = {
          playerId: editingPlayerId,
          mode: "manual",
          season: doc,
        };
      } else {
        payload = {
          playerId: editingPlayerId,
          mode: "json",
          seasonJson,
        };
      }
    } catch (error: any) {
      setSeasonSaveError(error?.message || "Failed to prepare season payload.");
      setSavingSeason(false);
      return;
    }

    try {
      const res = await fetch("/api/admin/database/season", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));
      if (res.status === 401) {
        setAuthenticated(false);
        setSeasonSaveError("Session expired. Log in again.");
        return;
      }

      if (!res.ok) {
        setSeasonSaveError(String(data?.error || "Failed to save season."));
        return;
      }

      setSeasonSaveMessage(String(data?.message || "Season saved successfully."));
      await loadDatabase();

      const shouldRunPredictions = window.confirm("Season saved successfully. Do you want to run the prediction script now?");
      cancelSeasonEditor();
      if (shouldRunPredictions) {
        await handleTriggerWorkflow();
      }
    } catch {
      setSeasonSaveError("Failed to save season due to a network error.");
    } finally {
      setSavingSeason(false);
    }
  }

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    setUploadError(null);
    setUploadResult(null);

    if (!files.length) {
      setUploadError("Select at least one JSON file.");
      return;
    }

    const threshold = Number(overAgeThreshold);
    if (!Number.isFinite(threshold) || threshold < 1) {
      setUploadError("Over-age threshold must be a positive number.");
      return;
    }

    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    formData.append("overAgeThreshold", String(Math.trunc(threshold)));

    setUploading(true);
    try {
      const res = await fetch("/api/admin/upload", {
        method: "POST",
        body: formData,
      });

      const data = (await res.json()) as UploadResponse;
      if (res.status === 401) {
        setAuthenticated(false);
        setUploadError("Session expired. Log in again.");
        return;
      }

      if (!res.ok) {
        setUploadError(data?.error || "Upload failed.");
        return;
      }

      setUploadResult(data);
      await loadDatabase();
      if (data.successes.some((result) => result.importKind === "tier-a")) {
        const shouldRunPredictions = window.confirm(
          "Tier A model data uploaded successfully. Do you want to refresh the stored predictions now?"
        );
        if (shouldRunPredictions) await handleTriggerWorkflow();
      }
    } catch {
      setUploadError("Upload failed due to a network error.");
    } finally {
      setUploading(false);
    }
  }

  async function handleTriggerWorkflow() {
    setTriggerError(null);
    setTriggerMessage(null);
    setTriggering(true);

    try {
      const res = await fetch("/api/admin/trigger", {
        method: "POST",
      });
      const data = await res.json();

      if (res.status === 401) {
        setAuthenticated(false);
        setTriggerError("Session expired. Log in again.");
        return;
      }

      if (!res.ok) {
        setTriggerError(data?.error || "Failed to dispatch workflow.");
        return;
      }

      setTriggerMessage(
        data?.actionsUrl
          ? `Workflow dispatched. Check GitHub Actions: ${data.actionsUrl}`
          : "Workflow dispatched."
      );
    } catch {
      setTriggerError("Failed to dispatch workflow due to a network error.");
    } finally {
      setTriggering(false);
    }
  }

  if (loadingSession) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-20 text-white">
        <p>Loading admin session...</p>
      </main>
    );
  }

  if (!configured) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-20 text-white">
        <h1 className="text-3xl font-bold text-[#D4AF37]">Admin Dashboard</h1>
        <p className="mt-4 text-gray-300">
          Admin authentication is not configured on this deployment. Set
          <code className="mx-1 rounded bg-black px-1 py-0.5">ADMIN_DASHBOARD_PASSWORD</code>
          and
          <code className="mx-1 rounded bg-black px-1 py-0.5">ADMIN_SESSION_SECRET</code>
          in your deployment.
        </p>
      </main>
    );
  }

  if (!authenticated) {
    return (
      <main className="mx-auto max-w-md px-6 py-20 text-white">
        <h1 className="text-3xl font-bold text-[#D4AF37]">Admin Login</h1>
        <p className="mt-2 text-sm text-gray-300">Sign in to upload players and run predictions manually.</p>

        <form onSubmit={handleLogin} className="mt-8 space-y-4 rounded-xl border border-[#2A2A2A] bg-[#0B0B0B] p-6">
          <label className="block text-sm text-gray-200" htmlFor="admin-password">
            Password
          </label>
          <input
            id="admin-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-md border border-[#2A2A2A] bg-black px-3 py-2 text-white outline-none focus:border-[#D4AF37]"
            required
          />

          {loginError ? <p className="text-sm text-red-400">{loginError}</p> : null}

          <button
            type="submit"
            disabled={loggingIn}
            className="w-full rounded-md bg-[#D4AF37] px-4 py-2 font-semibold text-black disabled:opacity-60"
          >
            {loggingIn ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-14 text-white">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#D4AF37]">Admin Dashboard</h1>
          <p className="mt-2 text-sm text-gray-300">Manage player data and manually trigger prediction runs.</p>
          <p className="mt-1 text-xs text-gray-400">Database provider: {provider}</p>
        </div>
        <button
          onClick={handleLogout}
          className="rounded-md border border-[#2A2A2A] bg-black px-4 py-2 text-sm text-gray-200 hover:border-[#D4AF37]"
        >
          Log out
        </button>
      </div>

      <section className="rounded-xl border border-[#2A2A2A] bg-[#0B0B0B] p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-[#D4AF37]">Database Viewer</h2>
            <p className="mt-2 text-sm text-gray-300">
              Live player data from your database. Expand a player to inspect and edit season-level stats.
            </p>
            <p className="mt-1 text-xs text-gray-400">
              Players: {dbTotals.players} | Seasons: {dbTotals.seasons}
            </p>
          </div>
          <button
            onClick={loadDatabase}
            disabled={dbLoading}
            className="rounded-md border border-[#2A2A2A] bg-black px-4 py-2 text-sm text-gray-200 hover:border-[#D4AF37] disabled:opacity-60"
          >
            {dbLoading ? "Refreshing..." : "Refresh Database"}
          </button>
        </div>

        {dbError ? <p className="mt-4 text-sm text-red-400">{dbError}</p> : null}

        {!dbLoading && !dbError && !dbPlayers.length ? (
          <p className="mt-4 text-sm text-gray-300">No players found in database.</p>
        ) : null}

        <div className="mt-5 max-h-[620px] space-y-3 overflow-y-auto pr-1">
          {dbPlayers.map((player) => (
            <details key={player.id} className="rounded-lg border border-[#2A2A2A] bg-black p-4">
              <summary className="cursor-pointer list-none">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{player.name}</p>
                    <p className="text-xs text-gray-400">{player.id}</p>
                  </div>
                  <div className="text-xs text-gray-300">
                    <span>Seasons: {player.season_count}</span>
                    <span className="mx-2">|</span>
                    <span>Career G/A: {player.career_totals.goals}/{player.career_totals.assists}</span>
                    <span className="mx-2">|</span>
                    <span>{player.is_retired ? "Retired" : "Active"}</span>
                    <span className="mx-2">|</span>
                    <span>{player.over_35 ? "Over 35" : "35 or under"}</span>
                  </div>
                </div>
              </summary>

              <div className="mt-4 border-t border-[#2A2A2A] pt-4 text-xs text-gray-300">
                <div className="mb-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <p>Nationality: {player.nationality || "-"}</p>
                  <p>Birth Date: {player.birth_date || "-"}</p>
                  <p>Retired Since: {player.retired_since || "-"}</p>
                  <p>Latest Season: {player.latest_season ? player.latest_season.season : "-"}</p>
                </div>

                <div className="mb-3 flex justify-end">
                  <button
                    onClick={() => startAddSeason(player.id, player.name)}
                    className="rounded-md border border-[#2A2A2A] bg-[#151515] px-3 py-1.5 text-xs font-semibold text-gray-100 hover:border-[#D4AF37]"
                  >
                    Add Season
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-[#2A2A2A] text-gray-400">
                        <th className="px-2 py-2">Season</th>
                        <th className="px-2 py-2">Team</th>
                        <th className="px-2 py-2">League</th>
                        <th className="px-2 py-2">Apps</th>
                        <th className="px-2 py-2">Goals</th>
                        <th className="px-2 py-2">Assists</th>
                        <th className="px-2 py-2">Minutes</th>
                        <th className="px-2 py-2">Rating</th>
                        <th className="px-2 py-2">xG</th>
                        <th className="px-2 py-2">xA</th>
                        <th className="px-2 py-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {player.seasons.map((season, index) => (
                        <tr key={`${player.id}-${season.season}-${season.team_id || "none"}-${index}`} className="border-b border-[#1C1C1C]">
                          <td className="px-2 py-2">{season.season}</td>
                          <td className="px-2 py-2">{season.team_id || "-"}</td>
                          <td className="px-2 py-2">{season.league_id || "-"}</td>
                          <td className="px-2 py-2">{season.appearances}</td>
                          <td className="px-2 py-2">{season.goals}</td>
                          <td className="px-2 py-2">{season.assists}</td>
                          <td className="px-2 py-2">{season.minutes}</td>
                          <td className="px-2 py-2">{season.rating ?? "-"}</td>
                          <td className="px-2 py-2">{season.xg ?? "-"}</td>
                          <td className="px-2 py-2">{season.xa ?? "-"}</td>
                          <td className="px-2 py-2">
                            <button
                              onClick={() => startEditSeason(player.id, player.name, season)}
                              className="rounded border border-[#2A2A2A] bg-[#151515] px-2 py-1 text-[11px] text-gray-100 hover:border-[#D4AF37]"
                            >
                              Edit
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>


              </div>
            </details>
          ))}
        </div>
      </section>

      <section className="mt-8 rounded-xl border border-[#2A2A2A] bg-[#0B0B0B] p-6">
        <h2 className="text-xl font-semibold text-[#D4AF37]">Upload Player JSON Files</h2>
        <p className="mt-2 text-sm text-gray-300">
          Accepts detailed player JSON (`player`, `teams`, `seasons`) and canonical Tier A JSON (`player_id`, `stat_scope`, `seasons`). Tier A uploads update the model input tables.
        </p>

        <form onSubmit={handleUpload} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm text-gray-200" htmlFor="player-files">Player JSON files</label>
            <input
              id="player-files"
              type="file"
              accept=".json,application/json"
              multiple
              onChange={(event) => setFiles(Array.from(event.target.files || []))}
              className="mt-2 block w-full rounded-md border border-[#2A2A2A] bg-black px-3 py-2 text-sm text-gray-200"
            />
            <p className="mt-2 text-xs text-gray-400">{selectedFileLabel}</p>
          </div>

          <div>
            <label className="block text-sm text-gray-200" htmlFor="over-age-threshold">Over-age threshold</label>
            <input
              id="over-age-threshold"
              type="number"
              min={1}
              value={overAgeThreshold}
              onChange={(event) => setOverAgeThreshold(event.target.value)}
              className="mt-2 w-40 rounded-md border border-[#2A2A2A] bg-black px-3 py-2 text-white"
            />
          </div>

          {uploadError ? <p className="text-sm text-red-400">{uploadError}</p> : null}

          <button
            type="submit"
            disabled={uploading}
            className="rounded-md bg-[#D4AF37] px-4 py-2 font-semibold text-black disabled:opacity-60"
          >
            {uploading ? "Uploading..." : "Upload to Database"}
          </button>
        </form>

        {uploadResult ? (
          <div className="mt-6 rounded-md border border-[#2A2A2A] bg-black p-4 text-sm">
            <p>Imported: {uploadResult.totals.imported}/{uploadResult.totals.filesReceived} files</p>
            {uploadResult.failures.length ? (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-red-300">
                {uploadResult.failures.map((item) => (
                  <li key={item.file}>{item.file}: {item.error}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-green-300">All files imported successfully. Database view refreshed.</p>
            )}
          </div>
        ) : null}
      </section>

      <section className="mt-8 rounded-xl border border-[#2A2A2A] bg-[#0B0B0B] p-6">
        <h2 className="text-xl font-semibold text-[#D4AF37]">Run Tier A Predictions Now</h2>
        <p className="mt-2 text-sm text-gray-300">
          This reuses the approved one-season model and stores current appearance and goal forecasts. It does not retrain.
        </p>

        {predictionStatus ? (
          <div className="mt-5 grid gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-md border border-[#2A2A2A] bg-black p-3">
              <p className="text-gray-400">Approved model</p>
              <p className="mt-1 font-semibold text-white">{predictionStatus.approvedModels[0]?.version || "None"}</p>
            </div>
            <div className="rounded-md border border-[#2A2A2A] bg-black p-3">
              <p className="text-gray-400">Stored predictions</p>
              <p className="mt-1 font-semibold text-white">{predictionStatus.predictionCount}</p>
            </div>
            <div className="rounded-md border border-[#2A2A2A] bg-black p-3">
              <p className="text-gray-400">Latest run</p>
              <p className="mt-1 font-semibold text-white">{predictionStatus.recentRuns[0]?.status || "Never run"}</p>
            </div>
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            onClick={handleTriggerWorkflow}
            disabled={triggering}
            className="rounded-md bg-[#D4AF37] px-4 py-2 font-semibold text-black disabled:opacity-60"
          >
            {triggering ? "Triggering..." : "Run Next-Season Predictions"}
          </button>
          <button
            onClick={loadPredictionStatus}
            className="rounded-md border border-[#2A2A2A] bg-black px-4 py-2 text-sm text-gray-200 hover:border-[#D4AF37]"
          >
            Refresh Run Status
          </button>
        </div>

        {triggerMessage ? <p className="mt-4 text-sm text-green-300">{triggerMessage}</p> : null}
        {triggerError ? <p className="mt-4 text-sm text-red-400">{triggerError}</p> : null}
      </section>
      {editingPlayerId ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 px-4 py-8" role="dialog" aria-modal="true">
          <button
            type="button"
            aria-label="Close season editor"
            disabled={savingSeason}
            onClick={cancelSeasonEditor}
            className="absolute inset-0 cursor-default"
          />

          <div className="relative z-10 w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-xl border border-[#2A2A2A] bg-[#090909] p-5 text-white">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-lg font-semibold text-[#D4AF37]">
                  {editingSeasonKey === "new" ? "Add New Season" : "Edit Season"}
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  {editingPlayerName} ({editingPlayerId})
                </p>
              </div>

              <div className="flex items-center gap-4 text-xs text-gray-200">
                <label className="inline-flex items-center gap-2">
                  <input
                    type="radio"
                    name="season-editor-mode-modal"
                    checked={editorMode === "manual"}
                    onChange={() => handleEditorModeChange("manual")}
                  />
                  Manual Form
                </label>
                <label className="inline-flex items-center gap-2">
                  <input
                    type="radio"
                    name="season-editor-mode-modal"
                    checked={editorMode === "json"}
                    onChange={() => handleEditorModeChange("json")}
                  />
                  JSON Input
                </label>
              </div>
            </div>

            {editorMode === "manual" ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {MANUAL_FIELDS.map((field) => (
                  <label key={field.key} className="text-xs text-gray-200">
                    {field.label}
                    {field.required ? " *" : ""}
                    <input
                      value={manualDraft[field.key]}
                      onChange={(event) => setManualField(field.key, event.target.value)}
                      className="mt-1 w-full rounded border border-[#2A2A2A] bg-black px-2 py-1.5 text-white"
                    />
                  </label>
                ))}
              </div>
            ) : (
              <div className="mt-4">
                <label className="text-xs text-gray-200">
                  Season JSON (must be one season object)
                  <textarea
                    value={seasonJson}
                    onChange={(event) => setSeasonJson(event.target.value)}
                    rows={18}
                    className="mt-1 w-full rounded border border-[#2A2A2A] bg-black px-3 py-2 font-mono text-xs text-white"
                  />
                </label>
              </div>
            )}

            {seasonSaveError ? <p className="mt-3 text-sm text-red-400">{seasonSaveError}</p> : null}
            {seasonSaveMessage ? <p className="mt-3 text-sm text-green-300">{seasonSaveMessage}</p> : null}

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button
                onClick={handleSaveSeason}
                disabled={savingSeason}
                className="rounded-md bg-[#D4AF37] px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"
              >
                {savingSeason ? "Saving..." : "Save Season"}
              </button>
              <button
                onClick={cancelSeasonEditor}
                disabled={savingSeason}
                className="rounded-md border border-[#2A2A2A] bg-black px-4 py-2 text-sm text-gray-200 hover:border-[#D4AF37] disabled:opacity-60"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}

    </main>
  );
}
