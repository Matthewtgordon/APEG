"""Shopify order attribution logic with waterfall tier selection.

Attribution Tiers:
- Tier 1: customerJourneySummary.*Visit.utmParameters (Shopify native)
- Tier 2: Parse UTM from landingPage URL query params
- Tier 3: Parse UTM from referrerUrl URL query params
- Tier 0: No attribution available (NONE)
"""
import json
import logging
import re
from urllib.parse import parse_qs, urlparse


logger = logging.getLogger(__name__)


def _empty_utm() -> dict:
    return {
        "campaign": None,
        "source": None,
        "medium": None,
        "term": None,
        "content": None,
    }


def extract_utm_from_customer_journey(order_node: dict) -> dict:
    """Extract UTM parameters from customerJourneySummary.

    Checks lastVisit first, then firstVisit.

    Args:
        order_node: Shopify Order GraphQL node

    Returns:
        dict with utm_* keys (nullable) + metadata
    """
    journey = order_node.get("customerJourneySummary")
    if not journey:
        return {"tier": 0, "utm": {}, "source": None}

    last_visit = journey.get("lastVisit") or {}
    utm_params = last_visit.get("utmParameters") or {}

    if utm_params.get("campaign"):
        return {
            "tier": 1,
            "utm": {
                "campaign": utm_params.get("campaign"),
                "source": utm_params.get("source"),
                "medium": utm_params.get("medium"),
                "term": utm_params.get("term"),
                "content": utm_params.get("content"),
            },
            "source": "lastVisit.utmParameters",
        }

    first_visit = journey.get("firstVisit") or {}
    utm_params = first_visit.get("utmParameters") or {}

    if utm_params.get("campaign"):
        return {
            "tier": 1,
            "utm": {
                "campaign": utm_params.get("campaign"),
                "source": utm_params.get("source"),
                "medium": utm_params.get("medium"),
                "term": utm_params.get("term"),
                "content": utm_params.get("content"),
            },
            "source": "firstVisit.utmParameters",
        }

    return {"tier": 0, "utm": {}, "source": None}


def parse_utm_from_url(url: str) -> dict:
    """Parse UTM parameters from URL query string.

    Args:
        url: Full URL (landingPage or referrerUrl)

    Returns:
        dict with utm_* keys (nullable)
    """
    if not url:
        return _empty_utm()

    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        return {
            "campaign": params.get("utm_campaign", [None])[0],
            "source": params.get("utm_source", [None])[0],
            "medium": params.get("utm_medium", [None])[0],
            "term": params.get("utm_term", [None])[0],
            "content": params.get("utm_content", [None])[0],
        }
    except Exception as exc:
        logger.warning("Failed to parse URL %s: %s", url[:100], exc)
        return _empty_utm()


def choose_attribution(order_node: dict) -> dict:
    """Apply waterfall attribution algorithm.

    Tier 1: Native customerJourneySummary.utmParameters
    Tier 2: Parse landingPage URL
    Tier 3: Parse referrerUrl URL
    Tier 0: No attribution

    Args:
        order_node: Shopify Order GraphQL node

    Returns:
        Attribution record with:
        - utm_source/medium/campaign/term/content (nullable)
        - attribution_tier (0-3)
        - confidence (0.0-1.0)
        - evidence_json (compact JSON string)
    """
    tier1 = extract_utm_from_customer_journey(order_node)
    if tier1["tier"] == 1:
        return {
            "utm_source": tier1["utm"]["source"],
            "utm_medium": tier1["utm"]["medium"],
            "utm_campaign": tier1["utm"]["campaign"],
            "utm_term": tier1["utm"]["term"],
            "utm_content": tier1["utm"]["content"],
            "attribution_tier": 1,
            "confidence": 1.0,
            "evidence_json": json.dumps(
                {
                    "tier": 1,
                    "source": tier1["source"],
                    "utm": tier1["utm"],
                },
                separators=(",", ":"),
            ),
        }

    journey = order_node.get("customerJourneySummary") or {}
    last_visit = journey.get("lastVisit") or {}
    landing_page = last_visit.get("landingPage")

    if landing_page:
        utm = parse_utm_from_url(landing_page)
        if utm.get("campaign"):
            return {
                "utm_source": utm["source"],
                "utm_medium": utm["medium"],
                "utm_campaign": utm["campaign"],
                "utm_term": utm["term"],
                "utm_content": utm["content"],
                "attribution_tier": 2,
                "confidence": 0.8,
                "evidence_json": json.dumps(
                    {
                        "tier": 2,
                        "source": "landingPage",
                        "url": landing_page,
                        "utm": utm,
                    },
                    separators=(",", ":"),
                ),
            }

    referrer_url = last_visit.get("referrerUrl")
    if referrer_url:
        utm = parse_utm_from_url(referrer_url)
        if utm.get("campaign"):
            return {
                "utm_source": utm["source"],
                "utm_medium": utm["medium"],
                "utm_campaign": utm["campaign"],
                "utm_term": utm["term"],
                "utm_content": utm["content"],
                "attribution_tier": 3,
                "confidence": 0.6,
                "evidence_json": json.dumps(
                    {
                        "tier": 3,
                        "source": "referrerUrl",
                        "url": referrer_url,
                        "utm": utm,
                    },
                    separators=(",", ":"),
                ),
            }

    return {
        "utm_source": None,
        "utm_medium": None,
        "utm_campaign": None,
        "utm_term": None,
        "utm_content": None,
        "attribution_tier": 0,
        "confidence": 0.0,
        "evidence_json": json.dumps(
            {
                "tier": 0,
                "reason": "No UTM parameters found in customerJourneySummary or URLs",
            },
            separators=(",", ":"),
        ),
    }


def match_strategy_tag(utm_campaign: str | None, catalog: list[str]) -> dict:
    """Match utm_campaign to strategy_tag from catalog.

    Matching rules (in order):
    1. Exact match (case-insensitive)
    2. Substring contains (case-insensitive)
    3. Normalized slug match (replace spaces/underscores, remove non-alnum)

    Args:
        utm_campaign: UTM campaign parameter (nullable)
        catalog: List of strategy_tags from catalog

    Returns:
        dict with strategy_tag (nullable) and match_rule
    """
    if not utm_campaign or not catalog:
        return {"strategy_tag": None, "match_rule": "NONE"}

    utm_lower = utm_campaign.lower()

    for tag in catalog:
        if tag.lower() == utm_lower:
            return {"strategy_tag": tag, "match_rule": "EXACT"}

    for tag in catalog:
        if tag.lower() in utm_lower or utm_lower in tag.lower():
            return {"strategy_tag": tag, "match_rule": "SUBSTRING"}

    def normalize(value: str) -> str:
        value = value.replace(" ", "_").replace("-", "_")
        return re.sub(r"[^a-z0-9_]", "", value.lower())

    utm_slug = normalize(utm_campaign)

    for tag in catalog:
        if normalize(tag) == utm_slug:
            return {"strategy_tag": tag, "match_rule": "SLUG"}

    return {"strategy_tag": None, "match_rule": "NONE"}
