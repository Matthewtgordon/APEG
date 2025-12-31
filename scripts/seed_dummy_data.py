import sqlite3
import random
from datetime import datetime, timedelta
import json

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
        "cvr": 0.002, # 0.2% Conversion (Bad - needs SEO fix)
        "aov": 45.0
    }
]

def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clean old dummy data if needed (optional)
    # cursor.execute("DELETE FROM metrics_meta_daily") 
    # cursor.execute("DELETE FROM order_attributions")

    print(f"Seeding data for the last {DAYS_BACK} days...")

    for day in range(DAYS_BACK):
        date_str = (datetime.now() - timedelta(days=day)).strftime("%Y-%m-%d")
        
        for scenario in SCENARIOS:
            # 1. Generate Meta Metrics
            impressions = int(scenario['daily_spend'] / 1.5 * 100) # Approx $15 CPM
            clicks = int(impressions * scenario['ctr'])
            spend = scenario['daily_spend']
            
            # Insert Meta Metric
            cursor.execute("""
                INSERT INTO metrics_meta_daily (
                    metric_date, entity_type, entity_id, campaign_id, account_id, 
                    spend, impressions, ctr, outbound_clicks
                ) VALUES (?, 'campaign', ?, ?, 'act_DUMMY', ?, ?, ?, ?)
            """, (
                date_str, 
                f"cmp_{scenario['strategy_tag']}", 
                f"cmp_{scenario['strategy_tag']}", 
                spend, 
                impressions, 
                scenario['ctr'], 
                clicks
            ))

            # 2. Generate Shopify Orders (Attribution)
            orders_count = int(clicks * scenario['cvr'])
            for i in range(orders_count):
                order_id = f"ord_{scenario['strategy_tag']}_{date_str}_{i}"
                revenue = scenario['aov'] + random.uniform(-5, 5)
                
                cursor.execute("""
                    INSERT INTO order_attributions (
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

    conn.commit()
    conn.close()
    print("✅ Database seeded with 'Time Machine' data.")

if __name__ == "__main__":
    seed_data()