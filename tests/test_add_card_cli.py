import argparse, builtins
from types import SimpleNamespace
from mtg_importer import cli

class DummyNotion:
    def __init__(self, token):
        self.created = None
    def verify_token(self):
        return True
    def get_parent(self, page_id):
        return SimpleNamespace(status_code=200)
    def search_db_by_title(self, title):
        return {"id": "db"}
    def create_database(self, parent, title):
        return {"id": "db"}
    def ensure_columns(self, db_id):
        pass
    def get_title_property_name(self, db_id):
        return "Name"
    def query_by_card_id(self, db_id, card_id):
        return None
    def create_card_page(self, db_id, props):
        self.created = props
    def upload_images(self, urls):
        return []


def _cards():
    return [
        {"name": "Card A", "set": "aaa", "collector_number": "1", "rarity": "common", "id": "id1", "oracle_id": "oid1", "image_uris": {"normal": "u1"}, "promo_types": [], "lang": "en"},
        {"name": "Card A", "set": "bbb", "collector_number": "2", "rarity": "rare", "id": "id2", "oracle_id": "oid2", "image_uris": {"normal": "u2"}, "promo_types": [], "lang": "en"},
    ]


def test_add_card_creates_selected_print(monkeypatch):
    cards = _cards()
    monkeypatch.setattr(cli, "search_prints", lambda name, setcode=None: cards)
    dummy = DummyNotion("tok")
    monkeypatch.setattr(cli, "NotionClient", lambda token: dummy)
    inputs = iter(["2", "y"])
    monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
    args = argparse.Namespace(name="Card A", set=None, db_title="DB", parent="p", token="tok", dry_run=False)
    cli.cmd_add_card(args)
    assert dummy.created is not None
    assert dummy.created["Card ID"]["rich_text"][0]["text"]["content"] == "id2"


def test_add_card_cancel(monkeypatch):
    cards = _cards()
    monkeypatch.setattr(cli, "search_prints", lambda name, setcode=None: cards)
    dummy = DummyNotion("tok")
    monkeypatch.setattr(cli, "NotionClient", lambda token: dummy)
    inputs = iter([""])
    monkeypatch.setattr(builtins, "input", lambda _: next(inputs, ""))
    args = argparse.Namespace(name="Card A", set=None, db_title="DB", parent="p", token="tok", dry_run=False)
    cli.cmd_add_card(args)
    assert dummy.created is None
