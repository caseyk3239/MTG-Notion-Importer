from mtg_importer.scry import procurement_methods
def mk(setcode, promos=None):
    return {"set": setcode.lower(), "promo_types": promos or []}
def test_fin():
    assert "Play Booster" in procurement_methods(mk("FIN"))
    assert "Collector Booster" in procurement_methods(mk("FIN"))
def test_fca():
    vals = procurement_methods(mk("FCA"))
    assert "Play Booster (1-in-3 slot)" in vals and "Collector Booster" in vals
def test_fic():
    vals = procurement_methods(mk("FIC"))
    assert "Commander Deck" in vals
    vals2 = procurement_methods(mk("FIC", ["extendedart"]))
    assert "Collector Booster" in vals2
