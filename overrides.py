import json, pathlib, typing as t

def load_overrides() -> dict:
    p = pathlib.Path("overrides.json")
    if not p.exists(): return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict): return data
    except Exception:
        pass
    return {}

def apply_overrides(key: str, rec: dict, ov: dict) -> dict:
    # key can be SET-collector or Scryfall id; try both
    out = dict(rec)
    if key in ov and isinstance(ov[key], dict):
        o = ov[key]
        if "procurement" in o and isinstance(o["procurement"], list):
            out["procurement"] = list({str(x) for x in o["procurement"]})
        if "title" in o and isinstance(o["title"], str):
            out["title_override"] = o["title"]
    # also try by Scryfall id
    cid = rec.get("id")
    if cid and cid in ov and isinstance(ov[cid], dict):
        o = ov[cid]
        if "procurement" in o and isinstance(o["procurement"], list):
            out["procurement"] = list({str(x) for x in o["procurement"]})
        if "title" in o and isinstance(o["title"], str):
            out["title_override"] = o["title"]
    return out
