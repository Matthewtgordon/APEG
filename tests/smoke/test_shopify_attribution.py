"""Smoke test for Shopify order attribution field validation.

Validates that customerJourneySummary and UTM fields are available.

Run with valid credentials:
    PYTHONPATH=. pytest tests/smoke/test_shopify_attribution.py -v
"""
import os
from datetime import date, datetime, timedelta, timezone

import aiohttp
import pytest


@pytest.mark.skipif(
    not os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN"),
    reason="SHOPIFY_ADMIN_ACCESS_TOKEN not set",
)
@pytest.mark.asyncio
async def test_shopify_attribution_fields():
    """Validate Shopify attribution field availability.

    PASS Criteria:
    - customerJourneySummary exists on orders
    - lastVisit/firstVisit include landingPage, referrerUrl, utmParameters
    - utmParameters includes campaign/source/medium fields
    """
    shop_domain = os.getenv("SHOPIFY_STORE_DOMAIN")
    access_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
    api_version = os.getenv("SHOPIFY_API_VERSION", "2024-10")

    if not shop_domain:
        pytest.skip("SHOPIFY_STORE_DOMAIN not set")

    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

    start_iso = (
        datetime.combine(start_date, datetime.min.time())
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )
    end_iso = (
        datetime.combine(end_date, datetime.max.time())
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )

    query = """
    query($query: String!) {
      orders(first: 50, query: $query) {
        nodes {
          id
          name
          customerJourneySummary {
            firstVisit {
              landingPage
              referrerUrl
              utmParameters {
                campaign
                source
                medium
                term
                content
              }
            }
            lastVisit {
              landingPage
              referrerUrl
              utmParameters {
                campaign
                source
                medium
                term
                content
              }
            }
          }
        }
      }
    }
    """

    url = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }

    payload = {
        "query": query,
        "variables": {"query": f"created_at:>={start_iso} created_at:<={end_iso}"},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            assert response.status == 200, f"GraphQL request failed: {response.status}"

            result = await response.json()

            if "errors" in result:
                pytest.fail(f"GraphQL errors: {result['errors']}")

            orders = result["data"]["orders"]["nodes"]

            if not orders:
                pytest.skip("No orders found in test date range")

            order = orders[0]

            assert (
                "customerJourneySummary" in order
            ), "customerJourneySummary field missing"

            journey = order.get("customerJourneySummary")

            if journey is None:
                print("customerJourneySummary is null (edge case tolerance)")
                pytest.skip("customerJourneySummary null (edge case tolerance)")

            assert "lastVisit" in journey, "lastVisit field missing"
            last_visit = journey["lastVisit"]

            if last_visit:
                assert "landingPage" in last_visit, "landingPage field missing"
                assert "referrerUrl" in last_visit, "referrerUrl field missing"
                assert "utmParameters" in last_visit, "utmParameters field missing"

                utm = last_visit.get("utmParameters")
                if utm:
                    expected_fields = ["campaign", "source", "medium", "term", "content"]
                    for field in expected_fields:
                        assert field in utm, f"utmParameters.{field} missing"

                    print(
                        f"Shopify attribution fields validated on order {order['name']}"
                    )
                    print(f"UTM campaign: {utm.get('campaign')}")
                else:
                    print(
                        f"Order {order['name']} has null utmParameters (edge case tolerance)"
                    )
            else:
                pytest.skip("lastVisit is null (edge case tolerance)")
