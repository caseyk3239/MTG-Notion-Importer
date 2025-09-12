# MTG Notion Importer — Fresh Start

This simple app creates/uses **one shared Notion database** (`MTG – Cards`) and imports Magic: The Gathering sets from Scryfall (defaults: **FIN**, **FIC**, **FCA**). It also adds **Power** and **Toughness** columns and includes **both faces** for double‑faced cards.

## You will need
- A Notion **API token** (`ntn_...` or `secret_...`).
- Grant that integration access to your target page: open the parent page → **•••** → **Add connections** → select your integration.

Parent page id (pre-filled in the app): `250e0945-9e39-80fc-a408-c7d09ab28763`.

## Mac: Double-click launcher
1. Move this folder anywhere you like (e.g., `Documents/MTG-Importer`).
2. Double-click **Run MTG Notion Importer.command**.
3. A browser window opens. Paste your Notion token, confirm the parent page id, and sets (`fin fic fca`), then click **Run import**.

If the launcher doesn’t open, see the “If double‑click fails” section below.

## Windows / Terminal
```bash
python -m venv .venv
.\.venv\Scriptsctivate  # (Windows)  OR  source .venv/bin/activate  # (macOS/Linux)
pip install -r requirements.txt
streamlit run mtg_importer/app.py
```

## If double-click fails (macOS permissions)
Open Terminal, then:
```bash
cd "<the folder you unzipped>"
chmod +x "Run MTG Notion Importer.command"
./"Run MTG Notion Importer.command"
```
