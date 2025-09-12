import time, requests
from typing import Dict, Any, List, Optional, Set
from .util import cn_sort as _cn_sort

SCRY = "https://api.scryfall.com"

def _get(url: str, **params) -> requests.Response:
    return requests.get(url, params=params or None, timeout=60)

def fetch_set(code: str) -> List[Dict[str, Any]]:
    url = f"{SCRY}/cards/search"
    params = {"q": f"set:{code}", "unique": "prints"}
    out: List[Dict[str, Any]] = []
    while True:
        r = _get(url, **params)
        if r.status_code == 429:
            time.sleep(2); continue
        if r.status_code == 404:
            break
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("data", []))
        if not data.get("has_more"):
            break
        url, params = data.get("next_page"), {}
    return out

def fetch_named(name: str, setcode: Optional[str] = None, fuzzy: bool = False) -> Optional[Dict[str, Any]]:
    params = {"exact": name} if not fuzzy else {"fuzzy": name}
    if setcode: params["set"] = setcode
    r = _get(f"{SCRY}/cards/named", **params)
    return r.json() if r.status_code == 200 else None

def search_prints(name: str, setcode: Optional[str] = None) -> List[Dict[str, Any]]:
    q = f'!"{name}"'
    if setcode: q += f" set:{setcode}"
    url = f"{SCRY}/cards/search"
    params = {"q": q, "unique": "prints"}
    out: List[Dict[str, Any]] = []
    while True:
        r = _get(url, **params)
        if r.status_code == 429:
            time.sleep(2); continue
        if r.status_code == 404:
            break
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("data", []))
        if not data.get("has_more"):
            break
        url, params = data.get("next_page"), {}
    return out

def _from_uris(uris: Dict[str, str]) -> Optional[str]:
    return (uris or {}).get("png") or (uris or {}).get("large") or (uris or {}).get("normal")

def image_urls(card: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    if "image_uris" in card:
        u = _from_uris(card["image_uris"])
        if u: urls.append(u)
    for face in card.get("card_faces") or []:
        u = _from_uris((face or {}).get("image_uris", {}))
        if u and u not in urls: urls.append(u)
    return urls[:2]

def merged(card: Dict[str, Any], key: str) -> Optional[str]:
    vals = []
    for f in card.get("card_faces") or []:
        v = f.get(key)
        if v: vals.append(str(v))
    return " // ".join(vals) if vals else None

def alt_name(card: Dict[str, Any]) -> Optional[str]:
    fn = card.get("flavor_name")
    if not fn:
        for f in card.get("card_faces") or []:
            if f.get("flavor_name"): fn = f["flavor_name"]; break
    if not fn:
        pn = card.get("printed_name")
        if pn and pn != (card.get("name") or ""):
            fn = pn
    return fn

def procurement_methods(card: Dict[str, Any]) -> List[str]:
    setcode = (card.get("set") or "").upper()
    promos: Set[str] = set((card.get("promo_types") or []))
    methods: Set[str] = set()
    if setcode == "FIN":
        methods.update({"Play Booster", "Collector Booster"})
    elif setcode == "FCA":
        methods.update({"Play Booster (1-in-3 slot)", "Collector Booster"})
    elif setcode == "FIC":
        methods.add("Commander Deck")
        promo_lower = {p.lower() for p in promos}
        if {"extendedart","borderless","showcase"} & promo_lower:
            methods.add("Collector Booster")
            methods.add("Commander Deck Sample Pack")
    return sorted(methods)

def normalize(card: Dict[str, Any]) -> Dict[str, Any]:
    oracle = card.get("name") or ""
    ff = alt_name(card) or ""
    cn = card.get("collector_number") or ""
    return {
        "name": oracle,
        "alt_name": ff,
        "set": (card.get("set") or "").upper(),
        "collector_number": cn,
        "rarity": (card.get("rarity") or "").capitalize(),
        "mana_cost": card.get("mana_cost") or merged(card, "mana_cost") or "",
        "cmc": card.get("cmc"),
        "type_line": card.get("type_line") or merged(card, "type_line") or "",
        "oracle_text": card.get("oracle_text") or merged(card, "oracle_text") or "",
        "colors": card.get("colors") or [],
        "color_identity": card.get("color_identity") or [],
        "scryfall_uri": card.get("scryfall_uri") or None,
        "oracle_id": card.get("oracle_id") or "",
        "id": card.get("id") or "",
        "image_urls": image_urls(card),
        "power": card.get("power") or merged(card, "power") or "",
        "toughness": card.get("toughness") or merged(card, "toughness") or "",
        "procurement": procurement_methods(card),
        "oracle_raw": oracle,
        "ff_raw": ff,
        "cn_sort": _cn_sort(cn),
    }
