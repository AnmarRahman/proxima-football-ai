import { createRequire } from "node:module";
import path from "node:path";
import type { DatabaseSync } from "node:sqlite";

export type SqliteValue = string | number | null;

const require = createRequire(import.meta.url);

function resolveSqlitePath(): string {
  const configured = process.env.SQLITE_DATABASE_PATH;
  if (configured) {
    return path.isAbsolute(configured) ? configured : path.resolve(process.cwd(), configured);
  }

  return path.resolve(process.cwd(), "..", "backend", "python", "data", "proxima.sqlite3");
}

function loadSqliteModule(): { DatabaseSync: typeof DatabaseSync } {
  try {
    return require("node:sqlite") as { DatabaseSync: typeof DatabaseSync };
  } catch {
    throw new Error(
      "SQLite provider requires Node.js with built-in node:sqlite support (Node 22+)."
    );
  }
}

function openSqlite(readOnly: boolean): DatabaseSync {
  const { DatabaseSync } = loadSqliteModule();
  return new DatabaseSync(resolveSqlitePath(), {
    readOnly,
    enableForeignKeyConstraints: true,
  });
}

export function withSqliteDatabase<T>(
  options: { readOnly?: boolean } | undefined,
  fn: (db: DatabaseSync) => T
): T {
  const db = openSqlite(options?.readOnly ?? false);
  try {
    return fn(db);
  } finally {
    db.close();
  }
}

export function sqliteAll<T>(sql: string, params: SqliteValue[] = []): T[] {
  return withSqliteDatabase({ readOnly: true }, (db) => {
    const stmt = db.prepare(sql);
    return stmt.all(...params) as T[];
  });
}

export function sqliteGet<T>(sql: string, params: SqliteValue[] = []): T | null {
  return withSqliteDatabase({ readOnly: true }, (db) => {
    const stmt = db.prepare(sql);
    const row = stmt.get(...params) as T | undefined;
    return row ?? null;
  });
}

export function sqliteRun(sql: string, params: SqliteValue[] = []): void {
  withSqliteDatabase(undefined, (db) => {
    db.prepare(sql).run(...params);
  });
}
