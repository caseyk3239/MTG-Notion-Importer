import argparse, sys, os, time, getpass, json
from typing import List, Dict, Any
from .notion_api import NotionClient
from .scry import fetch_set, normalize, search_prints
from .util import format_title, mask_token
from .overrides import load_overrides, apply_overrides

def _ts(): return time.strftime("[%Y-%m-%d %H:%M:%S]")

def build_props_for_create(rec: dict, title_prop: str, title_text: str, notion: NotionClient) -> Dict[str, Any]:
    def rt(v): return {"rich_text":[{"type":"text","text":{"content":v}}]} if v else {"rich_text":[]}
    def sel(v): return {"select":{"name":v}} if v else {"select":None}
    def ms(vs): return {"multi_select":[{"name":x} for x in (vs or [])]}
    def num(n): return {"number": float(n) if n is not None else None}
    def url(v): return {"url": v or None}
    def date(v): return {"date": {"start": v}} if v else {"date": None}
    files = notion.upload_images(rec.get("image_urls"))
    props = {
        title_prop: {"title":[{"type":"text","text":{"content": title_text}}]},
        "Set": sel(rec.get("set")),
        "Collector #": rt(rec.get("collector_number","")),
        "Rarity": sel(rec.get("rarity","")),
        "Language": sel(rec.get("lang")),
        "Released At": date(rec.get("released_at")),
        "Layout": sel(rec.get("layout")),
        "Artist": rt(rec.get("artist","")),
        "Prices": rt(json.dumps(rec.get("prices")) if rec.get("prices") else ""),
        "Legalities": rt(json.dumps(rec.get("legalities")) if rec.get("legalities") else ""),
        "Mana Cost": rt(rec.get("mana_cost","")),
        "CMC": num(rec.get("cmc")),
        "Type Line": rt(rec.get("type_line","")),
        "Oracle Text": rt(rec.get("oracle_text","")),
        "Colors": ms(rec.get("colors") or []),
        "Color Identity": ms(rec.get("color_identity") or []),
        "Scryfall URL": url(rec.get("scryfall_uri")),
        "Oracle ID": rt(rec.get("oracle_id","")),
        "Card ID": rt(rec.get("id","")),
        "Power": rt(rec.get("power","")),
        "Toughness": rt(rec.get("toughness","")),
        "Procurement Method": ms(rec.get("procurement") or []),
        "Oracle Name": rt(rec.get("oracle_raw","")),
        "FF Name": rt(rec.get("ff_raw","")),
        "CN Sort": num(rec.get("cn_sort")),
    }
    if files:
        props["Image"] = {"files": files}
    return props

def build_props_for_update(title_prop: str, title_text: str, rec: dict, notion: NotionClient) -> Dict[str, Any]:
    def ms(vs): return {"multi_select":[{"name":x} for x in (vs or [])]}
    def rt(v): return {"rich_text":[{"type":"text","text":{"content":v}}]} if v else {"rich_text":[]}
    def num(n): return {"number": float(n) if n is not None else None}
    def sel(v): return {"select":{"name":v}} if v else {"select":None}
    def date(v): return {"date": {"start": v}} if v else {"date": None}
    files = notion.upload_images(rec.get("image_urls"))
    props = {
        title_prop: {"title":[{"type":"text","text":{"content": title_text}}]},
        "Language": sel(rec.get("lang")),
        "Released At": date(rec.get("released_at")),
        "Layout": sel(rec.get("layout")),
        "Artist": rt(rec.get("artist","")),
        "Prices": rt(json.dumps(rec.get("prices")) if rec.get("prices") else ""),
        "Legalities": rt(json.dumps(rec.get("legalities")) if rec.get("legalities") else ""),
        "Procurement Method": ms(rec.get("procurement") or []),
        "Oracle Name": rt(rec.get("oracle_raw","")),
        "FF Name": rt(rec.get("ff_raw","")),
        "CN Sort": num(rec.get("cn_sort")),
    }
    if files:
        props["Image"] = {"files": files}
    return props


def cmd_add_card(args):
    token = args.token or os.environ.get("NOTION_TOKEN") or getpass.getpass("Notion token (ntn_*): ").strip()
    print(_ts(), "Starting add-card — parent=", args.parent, ", token=", mask_token(token), ", name=", args.name)
    notion = NotionClient(token)
    if not notion.verify_token():
        print(_ts(), "Auth failed (401). Check your token & workspace."); sys.exit(2)
    r = notion.get_parent(args.parent)
    if r.status_code == 403:
        print(_ts(), "403: Invite the integration to the parent page (••• → Add connections)."); sys.exit(3)
    if r.status_code >= 300:
        print(_ts(), "Failed to open parent page:", r.status_code, r.text); sys.exit(4)

    db = notion.search_db_by_title(args.db_title)
    if not db:
        print(_ts(), "Creating database:", args.db_title)
        db = notion.create_database(args.parent, args.db_title)
    notion.ensure_columns(db["id"])
    title_prop = notion.get_title_property_name(db["id"])
    print(_ts(), "Using DB:", db["id"], "title property:", title_prop)

    prints = search_prints(args.name, args.set)
    if not prints:
        print(_ts(), "No prints found for", args.name)
        return
    for idx, card in enumerate(prints, start=1):
        rec = normalize(card)
        img = (rec.get("image_urls") or [""])[0]
        print(f"{idx}) {rec.get('set')} #{rec.get('collector_number')} {rec.get('rarity')} {img}")
    sel = input("Choose a print number to add (blank to cancel): ").strip()
    if not sel.isdigit():
        print(_ts(), "Cancelled")
        return
    choice = int(sel)
    if choice < 1 or choice > len(prints):
        print(_ts(), "Invalid selection")
        return
    rec = normalize(prints[choice - 1])
    title_text = format_title(rec["oracle_raw"], rec["ff_raw"], "Oracle — FF")
    existing = notion.query_by_card_id(db["id"], rec["id"])
    if existing:
        print(_ts(), "Card already exists in database")
        return
    if args.dry_run:
        print(_ts(), "Dry run: would create", title_text)
        return
    confirm = input(f"Add {title_text}? [y/N]: ").strip().lower()
    if not confirm.startswith("y"):
        print(_ts(), "Cancelled")
        return
    props = build_props_for_create(rec, title_prop, title_text, notion)
    notion.create_card_page(db["id"], props)
    print(_ts(), "Added", title_text)

def cmd_import(args):
    sets = [s.lower() for s in (args.sets or [])]
    token = args.token or os.environ.get("NOTION_TOKEN") or getpass.getpass("Notion token (ntn_*): ").strip()
    print(_ts(), "Starting import — parent=", args.parent, ", token=", mask_token(token), ", sets=", sets)
    notion = NotionClient(token)
    if not notion.verify_token():
        print(_ts(), "Auth failed (401). Check your token & workspace."); sys.exit(2)
    r = notion.get_parent(args.parent)
    if r.status_code == 403:
        print(_ts(), "403: Invite the integration to the parent page (••• → Add connections)."); sys.exit(3)
    if r.status_code >= 300:
        print(_ts(), "Failed to open parent page:", r.status_code, r.text); sys.exit(4)

    # DB ensure + title property
    db = notion.search_db_by_title(args.db_title)
    if not db:
        print(_ts(), "Creating database:", args.db_title)
        db = notion.create_database(args.parent, args.db_title)
    notion.ensure_columns(db["id"])
    title_prop = notion.get_title_property_name(db["id"])
    print(_ts(), "Using DB:", db["id"], "title property:", title_prop)

    overrides = load_overrides() if not args.no_overrides else {}
    created=updated=skipped=failed=0
    previews=[]
    for code in sets:
        print(_ts(), "Fetching Scryfall cards for", code.upper(), "…")
        cards = fetch_set(code)
        print(_ts(), "Fetched", len(cards), "prints for", code.upper())
        for item in cards:
            base = normalize(item)
            key = f'{base.get("set","")}-{base.get("collector_number","")}'
            rec = apply_overrides(key, base, overrides)
            title_text = rec.get("title_override") or format_title(rec["oracle_raw"], rec["ff_raw"], args.title_style)
            try:
                existing = notion.query_by_card_id(db["id"], rec["id"])
                if existing:
                    if args.dry_run:
                        if len(previews) < 16:
                            previews.append(f'UPDATE {key}: "{title_text}" | methods={rec.get("procurement")}')
                        updated += 1
                    else:
                        props = build_props_for_update(title_prop, title_text, rec, notion)
                        notion.update_card_minimal(existing["id"], props)
                        updated += 1
                else:
                    if args.dry_run:
                        if len(previews) < 16:
                            previews.append(f'CREATE {key}: "{title_text}" | methods={rec.get("procurement")}')
                        created += 1
                    else:
                        props = build_props_for_create(rec, title_prop, title_text, notion)
                        notion.create_card_page(db["id"], props)
                        created += 1
            except Exception as e:
                failed += 1
                if len(previews) < 16:
                    previews.append(f"ERROR {key}: {e}")

    if previews:
        print("\n--- PREVIEW (first changes) ---")
        for line in previews: print("  ", line)
    print("\n--- TOTALS ---")
    print("created=", created, "updated=", updated, "skipped=", skipped, "failed=", failed)

def build_parser():
    p = argparse.ArgumentParser(prog="mtg-importer", description="Scryfall → Notion importer")
    sub = p.add_subparsers(dest="cmd", required=True)

    ip = sub.add_parser("import", help="Import sets into a shared Notion database (UPSERT)")
    ip.add_argument("--sets", nargs="+", required=True, help="Set codes, e.g. fin fic fca")
    ip.add_argument("--db-title", required=True, help='Notion database title, e.g. "MTG – Cards"')
    ip.add_argument("--parent", required=True, help="Notion parent page ID")
    ip.add_argument("--token", help="Notion token (ntn_*)")
    ip.add_argument("--title-style", default="Oracle — FF", choices=["Oracle — FF","FF — Oracle","Oracle only"])
    ip.add_argument("--dry-run", action="store_true", help="No writes; show planned changes")
    ip.add_argument("--no-overrides", action="store_true", help="Ignore overrides.json")
    ip.set_defaults(func=cmd_import)

    ap = sub.add_parser("add-card", help="Search, preview, and add a single card")
    ap.add_argument("name", help="Exact card name")
    ap.add_argument("--set", help="Restrict to a set code")
    ap.add_argument("--db-title", required=True, help='Notion database title, e.g. "MTG – Cards"')
    ap.add_argument("--parent", required=True, help="Notion parent page ID")
    ap.add_argument("--token", help="Notion token (ntn_*)")
    ap.add_argument("--dry-run", action="store_true", help="No writes; show planned changes")
    ap.set_defaults(func=cmd_add_card)

    return p

def main(argv: List[str] | None = None):
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)
    args.func(args)

if __name__ == "__main__":
    main()
