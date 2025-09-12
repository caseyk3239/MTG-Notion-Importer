import time, requests, json
from typing import Dict, Any, Optional, List

NOTION = "https://api.notion.com/v1"
NV = "2022-06-28"

class NotionClient:
    def __init__(self, token: str):
        self.h = {"Authorization": f"Bearer {token}", "Notion-Version": NV, "Content-Type": "application/json"}

    # auth / lookup
    def verify_token(self) -> bool:
        return requests.get(f"{NOTION}/users/me", headers=self.h, timeout=30).status_code == 200

    def get_parent(self, page_id: str):
        return requests.get(f"{NOTION}/pages/{page_id}", headers=self.h, timeout=30)

    def search_db_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        body = {"query": title, "filter": {"property": "object", "value": "database"}}
        r = requests.post(f"{NOTION}/search", headers=self.h, data=json.dumps(body), timeout=60); r.raise_for_status()
        for it in r.json().get("results", []):
            if it.get("object") == "database":
                plain = "".join([(seg.get("plain_text") or "") for seg in (it.get("title") or [])])
                if plain == title:
                    return {"id": it["id"], "url": it.get("url")}
        return None

    def get_title_property_name(self, db_id: str) -> str:
        r = requests.get(f"{NOTION}/databases/{db_id}", headers=self.h, timeout=60); r.raise_for_status()
        for name, meta in (r.json().get("properties") or {}).items():
            if (meta or {}).get("type") == "title": return name
        return "Name"

    # schema
    def create_database(self, parent_page_id: str, title: str) -> Dict[str, Any]:
        props = {
            "Name": {"title": {}},
            "Set": {"select": {}},
            "Collector #": {"rich_text": {}},
            "Rarity": {"select": {}},
            "Mana Cost": {"rich_text": {}},
            "CMC": {"number": {}},
            "Type Line": {"rich_text": {}},
            "Oracle Text": {"rich_text": {}},
            "Colors": {"multi_select": {}},
            "Color Identity": {"multi_select": {}},
            "Scryfall URL": {"url": {}},
            "Oracle ID": {"rich_text": {}},
            "Card ID": {"rich_text": {}},
            "Power": {"rich_text": {}},
            "Toughness": {"rich_text": {}},
            "Image": {"files": {}},
            "Procurement Method": {"multi_select": {}},
            "Oracle Name": {"rich_text": {}},
            "FF Name": {"rich_text": {}},
            "CN Sort": {"number": {}},
        }
        body = {"parent":{"type":"page_id","page_id":parent_page_id},"title":[{"type":"text","text":{"content":title}}],"properties":props}
        r = requests.post(f"{NOTION}/databases", headers=self.h, data=json.dumps(body), timeout=60); r.raise_for_status()
        j = r.json(); return {"id": j["id"], "url": j.get("url")}

    def ensure_columns(self, db_id: str):
        need = {
            "Set": {"select": {}},
            "Collector #": {"rich_text": {}},
            "Rarity": {"select": {}},
            "Mana Cost": {"rich_text": {}},
            "CMC": {"number": {}},
            "Type Line": {"rich_text": {}},
            "Oracle Text": {"rich_text": {}},
            "Colors": {"multi_select": {}},
            "Color Identity": {"multi_select": {}},
            "Scryfall URL": {"url": {}},
            "Oracle ID": {"rich_text": {}},
            "Card ID": {"rich_text": {}},
            "Power": {"rich_text": {}},
            "Toughness": {"rich_text": {}},
            "Image": {"files": {}},
            "Procurement Method": {"multi_select": {}},
            "Oracle Name": {"rich_text": {}},
            "FF Name": {"rich_text": {}},
            "CN Sort": {"number": {}},
        }
        r = requests.get(f"{NOTION}/databases/{db_id}", headers=self.h, timeout=60); r.raise_for_status()
        existing = set((r.json().get("properties") or {}).keys())
        to_add = {k:v for k,v in need.items() if k not in existing}
        if to_add:
            pr = requests.patch(f"{NOTION}/databases/{db_id}", headers=self.h, data=json.dumps({"properties": to_add}), timeout=60)
            pr.raise_for_status()

    # data ops
    def query_by_card_id(self, db_id: str, card_id: str) -> Optional[Dict[str, Any]]:
        body = {"page_size":1, "filter":{"property":"Card ID","rich_text":{"equals": card_id}}}
        r = requests.post(f"{NOTION}/databases/{db_id}/query", headers=self.h, data=json.dumps(body), timeout=60); r.raise_for_status()
        res = r.json().get("results", [])
        return {"id": res[0]["id"], "url": res[0].get("url")} if res else None

    def create_card_page(self, db_id: str, properties: Dict[str, Any]):
        body = {"parent": {"database_id": db_id}, "properties": properties}
        r = requests.post(f"{NOTION}/pages", headers=self.h, data=json.dumps(body), timeout=60)
        if r.status_code == 429: time.sleep(1.2); r = requests.post(f"{NOTION}/pages", headers=self.h, data=json.dumps(body), timeout=60)
        r.raise_for_status(); return r.json().get("id")

    def update_card_minimal(self, page_id: str, properties: Dict[str, Any]):
        body = {"properties": properties}
        r = requests.patch(f"{NOTION}/pages/{page_id}", headers=self.h, data=json.dumps(body), timeout=60)
        if r.status_code == 429: time.sleep(1.2); r = requests.patch(f"{NOTION}/pages/{page_id}", headers=self.h, data=json.dumps(body), timeout=60)
        r.raise_for_status(); return True


    def update_card_page(self, page_id: str, properties: Dict[str, Any]):
        """Compat for older app code: patch full properties payload."""
        body = {"properties": properties}
        r = requests.patch(f"{NOTION}/pages/{page_id}", headers=self.h, data=json.dumps(body), timeout=60)
        if r.status_code == 429:
            time.sleep(1.2)
            r = requests.patch(f"{NOTION}/pages/{page_id}", headers=self.h, data=json.dumps(body), timeout=60)
        r.raise_for_status()
        return True
