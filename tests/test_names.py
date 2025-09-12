from mtg_importer.util import format_title
def test_format_title():
    assert format_title("Oracle","FF","Oracle — FF") == "Oracle — FF"
    assert format_title("Oracle","FF","FF — Oracle") == "FF — Oracle"
    assert format_title("Oracle","", "Oracle — FF") == "Oracle"
