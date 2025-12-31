"""Smoke test for Meta Marketing API field validation.

WARNING: Meta API official docs were unavailable (429).
This test validates that required fields are present in API responses.

Run with valid credentials:
    PYTHONPATH=. pytest tests/smoke/test_meta_api.py -v
"""
import os
from datetime import date, timedelta

import aiohttp
import pytest


@pytest.mark.skipif(
    not os.getenv("META_ACCESS_TOKEN"), reason="META_ACCESS_TOKEN not set"
)
@pytest.mark.asyncio
async def test_meta_insights_fields():
    """Validate Meta Insights API field availability.

    PASS Criteria:
    - HTTP 200 response
    - Response contains spend, impressions, ctr, cpc fields
    - outbound_clicks field exists OR actions array contains outbound_click
    """
    access_token = os.getenv("META_ACCESS_TOKEN")
    ad_account_id = os.getenv("META_AD_ACCOUNT_ID")

    if not ad_account_id:
        pytest.skip("META_AD_ACCOUNT_ID not set")

    if not ad_account_id.startswith("act_"):
        ad_account_id = f"act_{ad_account_id}"

    target_date = (date.today() - timedelta(days=1)).isoformat()

    url = f"https://graph.facebook.com/v18.0/{ad_account_id}/insights"
    params = {
        "access_token": access_token,
        "level": "ad",
        "time_increment": "1",
        "time_range": f'{{"since":"{target_date}","until":"{target_date}"}}',
        "fields": "spend,impressions,ctr,cpc,outbound_clicks",
        "limit": "10",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            assert response.status == 200, f"API request failed: {response.status}"

            result = await response.json()
            data = result.get("data", [])

            if not data:
                pytest.skip("No data returned for test date (no ad spend)")

            row = data[0]

            assert "spend" in row, "Missing 'spend' field"
            assert "impressions" in row, "Missing 'impressions' field"
            assert "ctr" in row, "Missing 'ctr' field"
            assert "cpc" in row, "Missing 'cpc' field"

            has_outbound_clicks_field = "outbound_clicks" in row

            has_outbound_in_actions = False
            if "actions" in row:
                for action in row["actions"]:
                    if action.get("action_type") == "outbound_click":
                        has_outbound_in_actions = True
                        break

            assert has_outbound_clicks_field or has_outbound_in_actions, (
                "outbound_clicks not found as direct field or in actions array. "
                "Available fields: " + ", ".join(row.keys())
            )

            print(f"Meta API fields validated: {', '.join(row.keys())}")
