"""Parse the outfield roster from PLAYER_SCRAPE_ROSTER.md.

Goalkeepers (section 1) are excluded. Sections 2-8 are outfield; each section
implies a position group used as the primary-position hint.
"""

import re
from pathlib import Path

ROSTER_MD = Path(__file__).resolve().parents[1] / "PLAYER_SCRAPE_ROSTER.md"

# section number -> (fine position group, coarse group)
SECTION_GROUPS = {
    2: ("CB", "DEF"),    # Centre-backs
    3: ("FB", "DEF"),    # Full-backs and Wing-backs
    4: ("DM", "MID"),    # Defensive Midfielders
    5: ("CM", "MID"),    # Central and Attacking Midfielders
    6: ("WNG", "WIDE"),  # Wingers and Inside Forwards
    7: ("FW", "FWD"),    # Strikers
    8: ("AM", "MID"),    # Hybrid Attackers and Number 10s
}

_HEADER_RE = re.compile(r"^##\s+(\d+)\.\s+(.*)$")
_ITEM_RE = re.compile(r"^\s*-\s*\[( |x|X)\]\s+(.+?)\s*$")


def parse_outfield_roster(path=ROSTER_MD):
    """Return a list of {name, section, section_title, position_group,
    coarse_group, marked_done} for every outfield player (sections 2-8)."""
    text = Path(path).read_text(encoding="utf-8")
    players = []
    section = None
    section_title = None
    for line in text.splitlines():
        h = _HEADER_RE.match(line)
        if h:
            section = int(h.group(1))
            section_title = h.group(2).strip()
            continue
        if section in SECTION_GROUPS:
            m = _ITEM_RE.match(line)
            if m:
                name = m.group(2).strip()
                pos, coarse = SECTION_GROUPS[section]
                players.append({
                    "name": name, "section": section, "section_title": section_title,
                    "position_group": pos, "coarse_group": coarse,
                    "marked_done": m.group(1).lower() == "x",
                })
    return players


if __name__ == "__main__":
    ps = parse_outfield_roster()
    from collections import Counter
    print(f"outfield players: {len(ps)}")
    print("by group:", dict(Counter(p["position_group"] for p in ps)))
    print("first 5:", [p["name"] for p in ps[:5]])
