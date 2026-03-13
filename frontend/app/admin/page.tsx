"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type SessionResponse = {
  authenticated: boolean;
  configured: boolean;
};

type UploadResult = {
  file: string;
  playerId?: string;
  seasonsImported?: number;
  error?: string;
};

type UploadResponse = {
  ok: boolean;
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
  rating: number | null;
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

export default function AdminPage() {
  const [loadingSession, setLoadingSession] = useState(true);
  const [configured, setConfigured] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

  const [dbLoading, setDbLoading] = useState(false);
  const [dbError, setDbError] = useState<string | null>(null);
  const [dbPlayers, setDbPlayers] = useState<AdminPlayer[]>([]);
  const [dbTotals, setDbTotals] = useState({ players: 0, seasons: 0 });

  const [files, setFiles] = useState<File[]>([]);
  const [overAgeThreshold, setOverAgeThreshold] = useState("35");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [triggering, setTriggering] = useState(false);
  const [triggerMessage, setTriggerMessage] = useState<string | null>(null);
  const [triggerError, setTriggerError] = useState<string | null>(null);

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
    } catch {
      setConfigured(false);
      setAuthenticated(false);
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
  }, [authenticated]);

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
          in your Vercel project.
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
              Live player data from your database. Expand a player to inspect season-level stats.
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

        <div className="mt-5 max-h-[520px] space-y-3 overflow-y-auto pr-1">
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
                    <span>
                      Career G/A: {player.career_totals.goals}/{player.career_totals.assists}
                    </span>
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
                  <p>
                    Latest Season: {player.latest_season ? player.latest_season.season : "-"}
                  </p>
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
          Files must match your existing schema (`player`, `teams`, `seasons`). Existing player rows are upserted.
        </p>

        <form onSubmit={handleUpload} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm text-gray-200" htmlFor="player-files">
              Player JSON files
            </label>
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
            <label className="block text-sm text-gray-200" htmlFor="over-age-threshold">
              Over-age threshold
            </label>
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
            {uploading ? "Uploading..." : "Upload to Supabase"}
          </button>
        </form>

        {uploadResult ? (
          <div className="mt-6 rounded-md border border-[#2A2A2A] bg-black p-4 text-sm">
            <p>
              Imported: {uploadResult.totals.imported}/{uploadResult.totals.filesReceived} files
            </p>
            {uploadResult.failures.length ? (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-red-300">
                {uploadResult.failures.map((item) => (
                  <li key={item.file}>
                    {item.file}: {item.error}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-green-300">All files imported successfully. Database view refreshed.</p>
            )}
          </div>
        ) : null}
      </section>

      <section className="mt-8 rounded-xl border border-[#2A2A2A] bg-[#0B0B0B] p-6">
        <h2 className="text-xl font-semibold text-[#D4AF37]">Run Predictions Now</h2>
        <p className="mt-2 text-sm text-gray-300">
          This dispatches your GitHub Actions workflow immediately instead of waiting for the weekly schedule.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            onClick={handleTriggerWorkflow}
            disabled={triggering}
            className="rounded-md bg-[#D4AF37] px-4 py-2 font-semibold text-black disabled:opacity-60"
          >
            {triggering ? "Triggering..." : "Trigger GitHub Action"}
          </button>
        </div>

        {triggerMessage ? <p className="mt-4 text-sm text-green-300">{triggerMessage}</p> : null}
        {triggerError ? <p className="mt-4 text-sm text-red-400">{triggerError}</p> : null}
      </section>
    </main>
  );
}
