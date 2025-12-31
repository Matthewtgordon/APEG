"""Unit tests for attribution logic."""
import json

from src.apeg_core.metrics.attribution import (
    choose_attribution,
    extract_utm_from_customer_journey,
    match_strategy_tag,
    parse_utm_from_url,
)


def test_parse_utm_from_url_with_params():
    """Test URL parsing with UTM parameters."""
    url = (
        "https://example.com/page?utm_source=facebook&"
        "utm_medium=cpc&utm_campaign=holiday_2024"
    )

    result = parse_utm_from_url(url)

    assert result["source"] == "facebook"
    assert result["medium"] == "cpc"
    assert result["campaign"] == "holiday_2024"
    assert result["term"] is None
    assert result["content"] is None


def test_parse_utm_from_url_no_params():
    """Test URL parsing without UTM parameters."""
    url = "https://example.com/page"

    result = parse_utm_from_url(url)

    assert all(value is None for value in result.values())


def test_extract_utm_tier1_lastvisit():
    """Test Tier 1 extraction from lastVisit.utmParameters."""
    order = {
        "customerJourneySummary": {
            "lastVisit": {
                "utmParameters": {
                    "campaign": "birthstone_march",
                    "source": "google",
                    "medium": "cpc",
                }
            }
        }
    }

    result = extract_utm_from_customer_journey(order)

    assert result["tier"] == 1
    assert result["utm"]["campaign"] == "birthstone_march"
    assert result["source"] == "lastVisit.utmParameters"


def test_extract_utm_tier1_firstvisit_fallback():
    """Test Tier 1 fallback to firstVisit.utmParameters."""
    order = {
        "customerJourneySummary": {
            "lastVisit": {"utmParameters": {}},
            "firstVisit": {
                "utmParameters": {"campaign": "initial_campaign", "source": "email"}
            },
        }
    }

    result = extract_utm_from_customer_journey(order)

    assert result["tier"] == 1
    assert result["utm"]["campaign"] == "initial_campaign"
    assert result["source"] == "firstVisit.utmParameters"


def test_choose_attribution_tier1():
    """Test Tier 1 attribution (native UTM parameters)."""
    order = {
        "customerJourneySummary": {
            "lastVisit": {
                "utmParameters": {
                    "campaign": "test_campaign",
                    "source": "test_source",
                    "medium": "test_medium",
                }
            }
        }
    }

    result = choose_attribution(order)

    assert result["attribution_tier"] == 1
    assert result["confidence"] == 1.0
    assert result["utm_campaign"] == "test_campaign"

    evidence = json.loads(result["evidence_json"])
    assert evidence["tier"] == 1
    assert evidence["source"] == "lastVisit.utmParameters"


def test_choose_attribution_tier2():
    """Test Tier 2 attribution (landingPage URL parsing)."""
    order = {
        "customerJourneySummary": {
            "lastVisit": {
                "utmParameters": {},
                "landingPage": (
                    "https://store.com/page?utm_campaign=landing_test&"
                    "utm_source=twitter"
                ),
            }
        }
    }

    result = choose_attribution(order)

    assert result["attribution_tier"] == 2
    assert result["confidence"] == 0.8
    assert result["utm_campaign"] == "landing_test"
    assert result["utm_source"] == "twitter"

    evidence = json.loads(result["evidence_json"])
    assert evidence["tier"] == 2
    assert evidence["source"] == "landingPage"


def test_choose_attribution_tier3():
    """Test Tier 3 attribution (referrerUrl URL parsing)."""
    order = {
        "customerJourneySummary": {
            "lastVisit": {
                "utmParameters": {},
                "landingPage": "https://store.com/page",
                "referrerUrl": "https://referrer.com?utm_campaign=referrer_test",
            }
        }
    }

    result = choose_attribution(order)

    assert result["attribution_tier"] == 3
    assert result["confidence"] == 0.6
    assert result["utm_campaign"] == "referrer_test"

    evidence = json.loads(result["evidence_json"])
    assert evidence["tier"] == 3
    assert evidence["source"] == "referrerUrl"


def test_choose_attribution_tier0():
    """Test Tier 0 (no attribution available)."""
    order = {
        "customerJourneySummary": {
            "lastVisit": {
                "utmParameters": {},
                "landingPage": "https://store.com/page",
            }
        }
    }

    result = choose_attribution(order)

    assert result["attribution_tier"] == 0
    assert result["confidence"] == 0.0
    assert result["utm_campaign"] is None

    evidence = json.loads(result["evidence_json"])
    assert evidence["tier"] == 0


def test_match_strategy_tag_exact():
    """Test exact match (case-insensitive)."""
    catalog = ["birthstone_march", "holiday_gifts", "wedding_bands"]

    result = match_strategy_tag("BIRTHSTONE_MARCH", catalog)

    assert result["strategy_tag"] == "birthstone_march"
    assert result["match_rule"] == "EXACT"


def test_match_strategy_tag_substring():
    """Test substring contains match."""
    catalog = ["birthstone_march", "holiday_gifts"]

    result = match_strategy_tag("march", catalog)

    assert result["strategy_tag"] == "birthstone_march"
    assert result["match_rule"] == "SUBSTRING"


def test_match_strategy_tag_slug():
    """Test normalized slug match."""
    catalog = ["Holiday Gifts 2024"]

    result = match_strategy_tag("holiday-gifts-2024", catalog)

    assert result["strategy_tag"] == "Holiday Gifts 2024"
    assert result["match_rule"] == "SLUG"


def test_match_strategy_tag_none():
    """Test no match."""
    catalog = ["birthstone_march", "holiday_gifts"]

    result = match_strategy_tag("unrelated_campaign", catalog)

    assert result["strategy_tag"] is None
    assert result["match_rule"] == "NONE"
