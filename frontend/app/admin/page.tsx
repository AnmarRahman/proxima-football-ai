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

export default function AdminPage() {
  const [loadingSession, setLoadingSession] = useState(true);
  const [configured, setConfigured] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [provider, setProvider] = useState("postgres");

  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

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
      setProvider(String(data.provider || "postgres"));
    } catch {
      setConfigured(false);
      setAuthenticated(false);
      setProvider("unknown");
    } finally {
      setLoadingSession(false);
    }
  }

  useEffect(() => {
    refreshSession();
  }, []);

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
    <main className="mx-auto max-w-5xl px-6 py-14 text-white">
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
            {uploading ? "Uploading..." : "Upload to Database"}
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
              <p className="mt-2 text-green-300">All files imported successfully.</p>
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
