from mtg_importer.util import cn_sort
def test_cn_sort_basic():
    assert cn_sort("101") == 101.0
def test_cn_sort_letter():
    assert cn_sort("101a") == 101.1
def test_cn_sort_dash():
    assert cn_sort("A-19") == 19.0
