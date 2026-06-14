from tools import search_listings


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception


def test_search_price_filter():
    # Non-vacuous: "jacket" has matches both above and below $50, so this
    # actually exercises the ceiling instead of passing on an empty list.
    results = search_listings("jacket", size=None, max_price=50)
    assert len(results) > 0
    assert all(item["price"] <= 50 for item in results)
    # The $75 leather bomber must be excluded by the ceiling.
    assert all("bomber" not in item["title"].lower() for item in results)


def test_search_price_ceiling_is_inclusive():
    # The 90s Track Jacket is priced at exactly 45.0 and should be kept.
    results = search_listings("track jacket", size=None, max_price=45)
    assert any(item["price"] == 45.0 for item in results)


def test_search_size_filter_matches_token():
    # "M" must match a listing sized "S/M", not just an exact "M".
    results = search_listings("baby tee", size="M", max_price=None)
    assert len(results) > 0
    assert any(item["size"] == "S/M" for item in results)


def test_search_size_filter_no_substring_false_positive():
    # "S" must NOT match the "s" inside a shoe size like "US 7" / "US 8".
    results = search_listings("platform shoes sneakers", size="S", max_price=None)
    assert all(not item["size"].lower().startswith("us") for item in results)


def test_search_results_sorted_by_relevance():
    # The listing matching every keyword ("Vintage Graphic Hoodie — Faded
    # Black") must rank ahead of listings that match only some of them.
    results = search_listings("vintage graphic hoodie faded black", size=None, max_price=None)
    assert len(results) > 1
    assert results[0]["id"] == "lst_015"
