import json

from mtg_importer.scry import normalize
from mtg_importer.cli import build_props_for_create, build_props_for_update


def _sample_card():
    return {
        "name": "Test Card",
        "set": "tst",
        "collector_number": "123",
        "rarity": "common",
        "mana_cost": "{1}{G}",
        "cmc": 2,
        "type_line": "Creature — Test",
        "oracle_text": "Test ability",
        "colors": ["G"],
        "color_identity": ["G"],
        "scryfall_uri": "http://example.com/card",
        "oracle_id": "oracle-123",
        "id": "id-123",
        "image_uris": {"normal": "http://example.com/image.jpg"},
        "power": "2",
        "toughness": "2",
        "promo_types": [],
        "lang": "en",
        "released_at": "2023-01-01",
        "layout": "normal",
        "artist": "John Doe",
        "prices": {"usd": "1.00", "eur": "0.90"},
        "legalities": {"standard": "not_legal", "modern": "legal"},
    }


class _DummyNotion:
    def upload_images(self, urls):
        return []


def test_normalize_extra_fields():
    rec = normalize(_sample_card())
    assert rec["lang"] == "en"
    assert rec["released_at"] == "2023-01-01"
    assert rec["layout"] == "normal"
    assert rec["artist"] == "John Doe"
    assert rec["prices"]["usd"] == "1.00"
    assert rec["legalities"]["modern"] == "legal"


def test_property_mapping_includes_new_fields():
    rec = normalize(_sample_card())
    props = build_props_for_create(rec, "Name", "Title", _DummyNotion())
    assert props["Language"]["select"]["name"] == "en"
    assert props["Released At"]["date"]["start"] == "2023-01-01"
    assert props["Layout"]["select"]["name"] == "normal"
    assert props["Artist"]["rich_text"][0]["text"]["content"] == "John Doe"
    assert json.loads(props["Prices"]["rich_text"][0]["text"]["content"]) == rec["prices"]
    assert json.loads(props["Legalities"]["rich_text"][0]["text"]["content"]) == rec["legalities"]

    props_u = build_props_for_update("Name", "Title", rec, _DummyNotion())
    assert props_u["Language"]["select"]["name"] == "en"
    assert props_u["Released At"]["date"]["start"] == "2023-01-01"
