import json
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.apeg_core.feedback.schema import init_feedback_schema
from src.apeg_core.metrics.schema import init_database

# Configuration
DB_PATH = "data/metrics.db"
DAYS_BACK = 7

# Scenarios to seed
SCENARIOS = [
    {
        "name": "Winner - Gold Necklace",
        "strategy_tag": "gold_necklace_scale",
        "daily_spend": 50.0,
        "ctr": 0.025, # 2.5% CTR (High)
        "cvr": 0.05,  # 5% Conversion Rate (High)
        "aov": 85.0   # Average Order Value
    },
    {
        "name": "Loser - Old Scarf",
        "strategy_tag": "winter_scarf_clearance",
        "daily_spend": 40.0,
        "ctr": 0.004, # 0.4% CTR (Low)
        "cvr": 0.00,  # 0% Conversion (Terrible)
        "aov": 0.0
    },
    {
        "name": "Fixable - Blue Ring",
        "strategy_tag": "blue_ring_traffic",
        "daily_spend": 30.0,
        "ctr": 0.03,  # 3% CTR (Great traffic)
        "cvr": 0.06,  # 6% Conversion (enough orders, low ROAS)
        "aov": 15.0
    }
]

def _load_seed_product_ids() -> list[str]:
    raw_ids = os.getenv("SEED_PRODUCT_IDS", "").strip()
    if raw_ids:
        return [value.strip() for value in raw_ids.split(",") if value.strip()]

    single_id = os.getenv("TEST_PRODUCT_ID", "").strip()
    if single_id:
        return [single_id]

    return []


def seed_data():
    init_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    init_feedback_schema(conn)
    cursor = conn.cursor()

    # Clean old dummy data if needed (optional)
    # cursor.execute("DELETE FROM metrics_meta_daily") 
    # cursor.execute("DELETE FROM order_attributions")

    seed_product_ids = _load_seed_product_ids()
    if not seed_product_ids:
        print(
            "⚠️  No TEST_PRODUCT_ID or SEED_PRODUCT_IDS set; "
            "using placeholder product IDs."
        )

    print(f"Seeding data for the last {DAYS_BACK} days...")

    for day in range(DAYS_BACK):
        date_str = (datetime.now() - timedelta(days=day)).strftime("%Y-%m-%d")

        for idx, scenario in enumerate(SCENARIOS):
            # 1. Generate Meta Metrics
            impressions = int(scenario['daily_spend'] / 1.5 * 100) # Approx $15 CPM
            clicks = int(impressions * scenario['ctr'])
            spend = scenario['daily_spend']
            campaign_id = f"cmp_{scenario['strategy_tag']}"

            raw_json = {
                "campaign_name": f"{scenario['name']} [{scenario['strategy_tag']}]"
            }

            # Insert Meta Metric
            cursor.execute("""
                INSERT OR REPLACE INTO metrics_meta_daily (
                    metric_date, entity_type, entity_id, campaign_id, account_id, 
                    spend, impressions, ctr, outbound_clicks, raw_json
                ) VALUES (?, 'campaign', ?, ?, 'act_DUMMY', ?, ?, ?, ?, ?)
            """, (
                date_str, 
                campaign_id, 
                campaign_id, 
                spend, 
                impressions, 
                scenario['ctr'], 
                clicks,
                json.dumps(raw_json, separators=(",", ":")),
            ))

            cursor.execute(
                """
                INSERT OR IGNORE INTO strategy_tag_mappings (
                    entity_type, entity_id, strategy_tag,
                    mapping_method, mapping_confidence, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "campaign",
                    campaign_id,
                    scenario["strategy_tag"],
                    "seed_dummy_data",
                    1.0,
                    json.dumps({"seeded": True}, separators=(",", ":")),
                ),
            )

            product_id = seed_product_ids[idx % len(seed_product_ids)] if seed_product_ids else (
                f"gid://shopify/Product/seed_{scenario['strategy_tag']}"
            )

            # 2. Generate Shopify Orders (Attribution)
            orders_count = int(clicks * scenario['cvr'])
            for i in range(orders_count):
                order_id = f"ord_{scenario['strategy_tag']}_{date_str}_{i}"
                revenue = scenario['aov'] + random.uniform(-5, 5)
                
                cursor.execute("""
                    INSERT OR IGNORE INTO order_attributions (
                        order_id, order_name, created_at, total_price, currency, 
                        attribution_tier, confidence, strategy_tag, evidence_json
                    ) VALUES (?, ?, ?, ?, 'USD', 1, 1.0, ?, '{}')
                """, (
                    order_id, 
                    f"Order #{random.randint(1000, 9999)}", 
                    f"{date_str}T12:00:00", 
                    revenue, 
                    scenario['strategy_tag']
                ))

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO order_line_attributions (
                        order_id, order_created_at, product_id, variant_id,
                        quantity, line_revenue, currency, strategy_tag,
                        attribution_tier, confidence, raw_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        f"{date_str}T12:00:00",
                        product_id,
                        None,
                        1,
                        revenue,
                        "USD",
                        scenario["strategy_tag"],
                        1,
                        1.0,
                        "seed_dummy_data",
                    ),
                )

    conn.commit()
    conn.close()
    print("✅ Database seeded with 'Time Machine' data.")

if __name__ == "__main__":
    seed_data()
