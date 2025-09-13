import re
from typing import List, Dict, Any
from collections import Counter

from .scry import search_prints, normalize


def parse_decklist(text: str) -> List[Dict[str, Any]]:
    """Parse a plaintext/markdown deck list.

    Returns list of items with keys: count, name, section (main/sideboard/command).
    """
    items: List[Dict[str, Any]] = []
    section = "main"
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        low = line.lower()
        if low.startswith("sideboard"):
            section = "sideboard"
            continue
        if low.startswith("commander") or low.startswith("command") or low.startswith("companion"):
            section = "command"
            continue
        m = re.match(r"(\d+)[xX]?\s+(.+)", line)
        if m:
            items.append({"count": int(m.group(1)), "name": m.group(2).strip(), "section": section})
    return items


def identify_cards(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Given parsed items, look up card printings and choose best match.

    Uses majority set preference, otherwise newest printing.
    """
    out: List[Dict[str, Any]] = []
    set_counts: Counter[str] = Counter()
    for it in items:
        prints = search_prints(it["name"]) or []
        chosen = None
        preferred = set_counts.most_common(1)[0][0] if set_counts else None
        if preferred:
            cand = [p for p in prints if (p.get("set") or "").upper() == preferred]
            if cand:
                chosen = max(cand, key=lambda c: c.get("released_at") or "")
        if not chosen and prints:
            chosen = max(prints, key=lambda c: c.get("released_at") or "")
        norm = normalize(chosen) if chosen else None
        if norm:
            set_counts[norm["set"]] += 1
        out.append({**it, "card": norm})
    return out
