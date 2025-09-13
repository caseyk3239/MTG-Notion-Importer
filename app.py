# bootstrap import path
import os, sys, time
ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(ROOT)
if PARENT not in sys.path: sys.path.insert(0, PARENT)

import streamlit as st
from typing import Dict, Any, List
import json
import pandas as pd

from mtg_importer.notion_api import NotionClient
from mtg_importer.scry import fetch_set, normalize
from mtg_importer.util import format_title
from mtg_importer.decklist import parse_decklist, identify_cards

st.set_page_config(page_title="MTG Notion Importer", page_icon="🗂️", layout="centered")
st.title("MTG – Notion Importer (Shared DB)")
st.caption(
    "UPSERT into one shared database. Existing pages: minimal update (Title, Procurement, Oracle/FF names, CN Sort). New pages: full create."
)

def props_create(notion: NotionClient, rec: Dict[str, Any], title_prop: str, title_text: str) -> Dict[str, Any]:
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

def props_update(notion: NotionClient, title_prop: str, title_text: str, rec: Dict[str, Any]) -> Dict[str, Any]:
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

def ensure_db(notion: NotionClient, parent_id: str, title: str):
    st.write(f"Looking for database titled “{title}”…")
    db = notion.search_db_by_title(title)
    if not db:
        st.write("Creating database…")
        db = notion.create_database(parent_id, title)
    notion.ensure_columns(db["id"])
    st.success(f"Using database: {db['id']}")
    return db

def verify(notion: NotionClient, parent: str) -> bool:
    st.write("Checking token with Notion…")
    if not notion.verify_token():
        st.error("Notion auth failed (401)."); return False
    st.write("Validating access to the parent page…")
    r = notion.get_parent(parent)
    if r.status_code == 403:
        st.error("Forbidden (403): On the parent page → ••• → Add connections → your integration."); return False
    if r.status_code >= 300:
        st.error(f"Failed to open parent page: {r.status_code} {r.text}"); return False
    return True

# UI
tab_sets, tab_decks = st.tabs(["Import sets", "Decks"])

with tab_sets:
    st.subheader("Import sets (UPSERT)")
    with st.form("run_sets_form"):
        token = st.text_input("Notion API token", type="password", help="ntn_*")
        parent_id = st.text_input("Parent page ID", value="250e0945-9e39-80fc-a408-c7d09ab28763")
        sets_str = st.text_input("Set codes (space-separated)", value="fca")
        db_title = st.text_input("Database title", value="MTG – Cards")
        title_style = st.selectbox("Title style", ["Oracle — FF", "FF — Oracle", "Oracle only"], index=0)
        update_existing = st.checkbox("Update existing pages", value=True)
        submitted = st.form_submit_button("Run import")

    if submitted:
        notion = NotionClient(token)
        if verify(notion, parent_id):
            db = ensure_db(notion, parent_id, db_title)
            title_prop = notion.get_title_property_name(db["id"])
            st.write(f"Using title property: **{title_prop}**")

            total_created = total_updated = total_skipped = total_failed = 0
            sample = []

            for code in [s.strip().lower() for s in sets_str.split() if s.strip()]:
                u = code.upper()
                st.write(f"Fetching Scryfall cards for **{u}**…")
                cards = fetch_set(code)
                st.write(f"Fetched **{len(cards)}** cards for {u}.")
                created = updated = skipped = failed = 0

                for item in cards:
                    rec = normalize(item)
                    new_title = format_title(rec.get("oracle_raw", ""), rec.get("ff_raw", ""), title_style)
                    try:
                        existing = notion.query_by_card_id(db["id"], rec["id"])
                        if existing:
                            if update_existing:
                                notion.update_card_minimal(existing["id"], props_update(notion, title_prop, new_title, rec))
                                updated += 1
                                if len(sample) < 10:
                                    sample.append(f'{u}-{rec.get("collector_number", "?")}: → {new_title}')
                            else:
                                skipped += 1
                        else:
                            notion.create_card_page(db["id"], props_create(notion, rec, title_prop, new_title))
                            created += 1
                    except Exception as e:
                        failed += 1
                        if len(sample) < 10:
                            sample.append(f'ERROR {u}-{rec.get("collector_number", "?")}: {e}')

                st.info(f"[{u}] created={created} updated={updated} skipped={skipped} failed={failed}")
                total_created += created
                total_updated += updated
                total_skipped += skipped
                total_failed += failed

            if sample:
                st.markdown("**Preview (first changes):**\n\n- " + "\n- ".join(sample))
            if total_failed:
                st.warning("Some items failed; see preview list above.")
            st.success(
                f"Totals — created={total_created} updated={total_updated} skipped={total_skipped} failed={total_failed}"
            )
            st.info(f"Database: {db.get('url')}")

with tab_decks:
    st.subheader("Import deck list")
    with st.form("deck_form"):
        token_d = st.text_input("Notion API token", type="password", key="deck_token")
        parent_id_d = st.text_input("Parent page ID", key="deck_parent")
        card_db_id = st.text_input("Card database ID", key="deck_card_db")
        decks_title = st.text_input("Decks database title", value="MTG – Decks")
        uploaded = st.file_uploader("Deck list file", type=["txt", "md"])
        deck_name = st.text_input("Deck name", value="")
        preview = st.form_submit_button("Preview")

    if preview and uploaded:
        text = uploaded.read().decode("utf-8")
        default_name = deck_name or os.path.splitext(uploaded.name)[0]
        items = identify_cards(parse_decklist(text))
        st.session_state["deck_preview"] = items
        st.session_state["deck_name"] = default_name
        df = pd.DataFrame(
            [
                {
                    "qty": it["count"],
                    "name": it["name"],
                    "set": (it["card"] or {}).get("set"),
                    "cn": (it["card"] or {}).get("collector_number"),
                    "section": it["section"],
                }
                for it in items
            ]
        )
        st.dataframe(df)

    if st.session_state.get("deck_preview"):
        if st.button("Tag cards in Notion"):
            notion = NotionClient(token_d)
            if verify(notion, parent_id_d):
                deck_db = notion.ensure_decks_db(parent_id_d, decks_title, card_db_id)
                deck_page = notion.create_deck_page(deck_db["id"], st.session_state.get("deck_name", "Deck"))
                card_ids: List[str] = []
                for it in st.session_state.get("deck_preview", []):
                    rec = it.get("card")
                    if not rec:
                        continue
                    existing = notion.query_by_card_id(card_db_id, rec["id"])
                    if existing:
                        notion.add_relation(existing["id"], "Decks", [deck_page])
                        card_ids.append(existing["id"])
                if card_ids:
                    notion.add_relation(deck_page, "Cards", card_ids)
                st.success("Deck tagging complete")
