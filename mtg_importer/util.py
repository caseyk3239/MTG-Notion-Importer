import re

def mask_token(tok: str) -> str:
    if not tok:
        return ""
    if len(tok) <= 8:
        return "token_***"
    return tok[:6] + "…" + tok[-4:]

def format_title(oracle: str, ff: str, style: str = "Oracle — FF") -> str:
    oracle = (oracle or "").strip()
    ff = (ff or "").strip()
    if style == "Oracle — FF":
        return f"{oracle} — {ff}" if ff else oracle
    if style == "FF — Oracle":
        return f"{ff} — {oracle}" if ff else oracle
    return oracle

def cn_sort(cn: str):
    if not cn:
        return None
    s = cn.strip().lower()
    # extract first number in the string
    m = re.search(r"(\d+)", s)
    if not m:
        return None
    base = int(m.group(1))
    # simple letter suffix like 101a -> 101.1 ; 101b -> 101.2
    m2 = re.match(r"^\d+([a-z])$", s)
    if m2:
        return base + (ord(m2.group(1)) - 96) / 10.0
    return float(base)
