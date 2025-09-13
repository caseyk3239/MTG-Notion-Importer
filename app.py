# bootstrap import path
import os, sys, time
ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(ROOT)
if PARENT not in sys.path: sys.path.insert(0, PARENT)

import streamlit as st
from typing import Dict, Any
import json

from mtg_importer.notion_api import NotionClient
from mtg_importer.scry import fetch_set, normalize, search_prints
from mtg_importer.util import format_title

st.set_page_config(page_title="MTG Notion Importer", page_icon="🗂️", layout="centered")
st.title("MTG – Notion Importer (Shared DB)")
st.caption("UPSERT into one shared database. Existing pages: minimal update (Title, Procurement, Oracle/FF names, CN Sort). New pages: full create.")

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

tab_sets, tab_single = st.tabs(["Import sets", "Add single card"])

with tab_sets:
    st.subheader("Import sets (UPSERT)")
    with st.form("run_sets_form"):
        token = st.text_input("Notion API token", type="password", help="ntn_*")
        parent_id = st.text_input("Parent page ID", value="250e0945-9e39-80fc-a408-c7d09ab28763")
        sets_str = st.text_input("Set codes (space-separated)", value="fca")
        db_title = st.text_input("Database title", value="MTG – Cards")
        title_style = st.selectbox("Title style", ["Oracle — FF","FF — Oracle","Oracle only"], index=0)
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
                    new_title = format_title(rec.get("oracle_raw",""), rec.get("ff_raw",""), title_style)
                    try:
                        existing = notion.query_by_card_id(db["id"], rec["id"])
                        if existing:
                            if update_existing:
                                notion.update_card_minimal(existing["id"], props_update(notion, title_prop, new_title, rec))
                                updated += 1
                                if len(sample) < 10:
                                    sample.append(f'{u}-{rec.get("collector_number","?")}: → {new_title}')
                            else:
                                skipped += 1
                        else:
                            notion.create_card_page(db["id"], props_create(notion, rec, title_prop, new_title))
                            created += 1
                    except Exception as e:
                        failed += 1
                        if len(sample) < 10:
                            sample.append(f'ERROR {u}-{rec.get("collector_number","?")}: {e}')

                st.info(f"[{u}] created={created} updated={updated} skipped={skipped} failed={failed}")
                total_created += created; total_updated += updated; total_skipped += skipped; total_failed += failed

            if sample:
                st.markdown("**Preview (first changes):**\n\n- " + "\n- ".join(sample))
            if total_failed:
                st.warning("Some items failed; see preview list above.")
            st.success(f"Totals — created={total_created} updated={total_updated} skipped={total_skipped} failed={total_failed}")
            st.info(f"Database: {db.get('url')}")

with tab_single:
    st.subheader("Add cards by search")
    # --- Part 1: search Scryfall ---
    with st.form("search_card_form"):
        card_name = st.text_input("Card name", value=st.session_state.get("card_name", ""))
        card_set = st.text_input("Set code (optional)", value=st.session_state.get("card_set", ""))
        search_submitted = st.form_submit_button("Search prints")

    if search_submitted:
        st.session_state["card_name"] = card_name
        st.session_state["card_set"] = card_set
        prints = [normalize(p) for p in search_prints(card_name, card_set or None)]
        st.session_state["prints"] = prints
        # clear previous selections
        for rec in prints:
            st.session_state.pop(f"sel_{rec['id']}", None)

    prints = st.session_state.get("prints")
    if prints:
        st.write("Select one or more prints to add:")
        cols = st.columns(3)
        for idx, rec in enumerate(prints):
            col = cols[idx % 3]
            with col:
                img = (rec.get("image_urls") or [""])[0]
                if img:
                    st.image(img, use_column_width=True)
                st.checkbox(f"{rec.get('set')} #{rec.get('collector_number')} {rec.get('rarity')}", key=f"sel_{rec['id']}")

        selected = [rec for rec in prints if st.session_state.get(f"sel_{rec['id']}")]
        if selected:
            # --- Part 2: Notion credentials and batch add ---
            with st.form("add_selected_form"):
                s_token = st.text_input("Notion API token", type="password", value=st.session_state.get("s_token", ""), help="ntn_*")
                s_parent = st.text_input("Parent page ID", value=st.session_state.get("s_parent", "250e0945-9e39-80fc-a408-c7d09ab28763"))
                s_db = st.text_input("Database title", value=st.session_state.get("s_db", "MTG – Cards"))
                s_title_style = st.selectbox("Title style", ["Oracle — FF","FF — Oracle","Oracle only"], index=0)
                add_submitted = st.form_submit_button(f"Add {len(selected)} card(s) to Notion")

            if add_submitted:
                st.session_state["s_token"] = s_token
                st.session_state["s_parent"] = s_parent
                st.session_state["s_db"] = s_db
                notion = NotionClient(s_token)
                if verify(notion, s_parent):
                    db = ensure_db(notion, s_parent, s_db)
                    title_prop = notion.get_title_property_name(db["id"])
                    added = skipped = 0
                    for rec in selected:
                        existing = notion.query_by_card_id(db["id"], rec["id"])
                        if existing:
                            skipped += 1
                            continue
                        title_text = format_title(rec.get("oracle_raw",""), rec.get("ff_raw",""), s_title_style)
                        props = props_create(notion, rec, title_prop, title_text)
                        notion.create_card_page(db["id"], props)
                        added += 1
                    st.success(f"Added {added} card(s); skipped {skipped} existing")
                    # reset state after adding
                    del st.session_state["prints"]
                    for rec in selected:
                        st.session_state.pop(f"sel_{rec['id']}", None)
