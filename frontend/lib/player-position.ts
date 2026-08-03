export type NormalizedPosition =
  | "striker"
  | "winger"
  | "attacking midfielder"
  | "central midfielder"
  | "defensive midfielder"
  | "fullback"
  | "centerback"
  | "goalkeeper";

const POSITION_GROUPS: Record<string, NormalizedPosition> = {
  FW: "striker",
  WNG: "winger",
  AM: "attacking midfielder",
  CM: "central midfielder",
  DM: "defensive midfielder",
  FB: "fullback",
  CB: "centerback",
  GK: "goalkeeper",
};

export function normalizePosition(
  positionGroup: unknown,
  primaryPosition: unknown,
  coarseGroup: unknown
): NormalizedPosition {
  const group = String(positionGroup || "").trim().toUpperCase();
  if (POSITION_GROUPS[group]) return POSITION_GROUPS[group];

  const raw = String(primaryPosition || "").trim().toLowerCase();
  if (raw.includes("goalkeeper") || raw.includes("keeper")) return "goalkeeper";
  if (raw.includes("centre-back") || raw.includes("center-back") || raw.includes("centerback")) return "centerback";
  if (raw.includes("full-back") || raw.includes("fullback") || raw.includes("wing-back")) return "fullback";
  if (raw.includes("defensive midfielder")) return "defensive midfielder";
  if (raw.includes("attacking midfielder")) return "attacking midfielder";
  if (raw.includes("central midfielder") || raw === "midfielder") return "central midfielder";
  if (raw.includes("winger") || raw.includes("wing half")) return "winger";
  if (raw.includes("forward") || raw.includes("striker")) return "striker";

  const coarse = String(coarseGroup || "").trim().toUpperCase();
  if (coarse === "GK") return "goalkeeper";
  if (coarse === "FWD") return "striker";
  if (coarse === "WIDE") return "winger";
  if (coarse === "MID") return "central midfielder";
  return "centerback";
}

export function formatPosition(position: string): string {
  return position.replace(/\b\w/g, (letter) => letter.toUpperCase());
}
