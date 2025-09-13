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

## Add individual cards
You can insert a single card into your Notion database from the web app or the terminal.

### Web app
Run `streamlit run mtg_importer/app.py` and open the **Add single card** tab.
Search for a card name (optionally restricting to a set) to preview all matching
prints and their images. Tick the prints you want, then enter your Notion token,
parent page and database title to batch-add the selected cards.

### Command line
```bash
python -m mtg_importer.cli add-card "Black Lotus" --db-title "MTG – Cards" --parent <PAGE_ID> --token <NOTION_TOKEN>
```

The CLI searches Scryfall for matching prints and displays a numbered preview
with the set code, collector number, rarity and image URL. Choose the desired
print and confirm to create the page. Use `--dry-run` to preview without writing
to Notion.
