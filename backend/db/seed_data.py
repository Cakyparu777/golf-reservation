"""Seed the database with sample golf courses and tee times.

Generates 5 courses and 30 days of tee times for each.
Run directly:
    python -m backend.db.seed_data
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.db.init_db import init_database
from backend.mcp_server.db.connection import get_connection

# ---------------------------------------------------------------------------
# Sample Data
# ---------------------------------------------------------------------------

COURSES = [
    {
        "name": "Pebble Beach Golf Links",
        "location": "Pebble Beach, CA",
        "latitude": 36.5725,
        "longitude": -121.9486,
        "holes": 18,
        "par": 72,
        "rating": 4.9,
        "phone": "(831) 622-8723",
        "amenities": '["pro_shop", "restaurant", "driving_range", "caddie_service", "ocean_views"]',
    },
    {
        "name": "Augusta National Golf Club",
        "location": "Augusta, GA",
        "latitude": 33.5030,
        "longitude": -82.0230,
        "holes": 18,
        "par": 72,
        "rating": 5.0,
        "phone": "(706) 667-6000",
        "amenities": '["pro_shop", "restaurant", "driving_range", "caddie_service", "clubhouse"]',
    },
    {
        "name": "Pine Valley Golf Club",
        "location": "Pine Valley, NJ",
        "latitude": 39.7884,
        "longitude": -74.9781,
        "holes": 18,
        "par": 70,
        "rating": 4.8,
        "phone": "(856) 783-3000",
        "amenities": '["pro_shop", "restaurant", "driving_range", "lodging"]',
    },
    {
        "name": "Shadow Creek Golf Course",
        "location": "North Las Vegas, NV",
        "latitude": 36.2572,
        "longitude": -115.1767,
        "holes": 18,
        "par": 72,
        "rating": 4.7,
        "phone": "(702) 399-7111",
        "amenities": '["pro_shop", "restaurant", "driving_range", "spa", "luxury_lounge"]',
    },
    {
        "name": "Torrey Pines Golf Course",
        "location": "La Jolla, CA",
        "latitude": 32.9005,
        "longitude": -117.2519,
        "holes": 18,
        "par": 72,
        "rating": 4.6,
        "phone": "(858) 452-3226",
        "amenities": '["pro_shop", "restaurant", "driving_range", "ocean_views", "practice_green"]',
    },
]

# Price tiers by time of day (USD)
PRICE_TIERS = {
    "early": 85.00,    # 6:00 – 7:30
    "prime": 150.00,   # 8:00 – 11:00
    "midday": 120.00,  # 11:30 – 14:00
    "afternoon": 95.00, # 14:30 – 16:00
    "twilight": 65.00, # 16:30 – 18:00
}

TEE_TIME_HOURS = [
    (6, 0), (6, 30), (7, 0), (7, 30),
    (8, 0), (8, 30), (9, 0), (9, 30),
    (10, 0), (10, 30), (11, 0), (11, 30),
    (12, 0), (12, 30), (13, 0), (13, 30),
    (14, 0), (14, 30), (15, 0), (15, 30),
    (16, 0), (16, 30), (17, 0), (17, 30),
]


def _get_price(hour: int, minute: int) -> float:
    """Determine price based on time of day."""
    t = hour * 60 + minute
    if t < 480:  # before 8:00
        return PRICE_TIERS["early"]
    elif t < 690:  # before 11:30
        return PRICE_TIERS["prime"]
    elif t < 840:  # before 14:00
        return PRICE_TIERS["midday"]
    elif t < 960:  # before 16:00
        return PRICE_TIERS["afternoon"]
    else:
        return PRICE_TIERS["twilight"]


def seed_database(db_path: Optional[Path] = None) -> None:
    """Insert sample courses and generate tee times for the next 30 days."""
    # Ensure tables exist
    init_database(db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Check if data already exists
        existing = cursor.execute("SELECT COUNT(*) FROM golf_courses").fetchone()[0]
        if existing > 0:
            print("⚠️  Database already contains data. Skipping seed.")
            return

        # Insert courses
        for course in COURSES:
            cursor.execute(
                """
                INSERT INTO golf_courses (name, location, latitude, longitude, holes, par, rating, phone, amenities)
                VALUES (:name, :location, :latitude, :longitude, :holes, :par, :rating, :phone, :amenities)
                """,
                course,
            )

        # Get course IDs
        course_ids = [row[0] for row in cursor.execute("SELECT id FROM golf_courses ORDER BY id").fetchall()]

        # Generate tee times for the next 30 days
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tee_time_count = 0

        for day_offset in range(30):
            date = today + timedelta(days=day_offset)

            for course_id in course_ids:
                # Each course has a small price multiplier based on rating
                course_row = cursor.execute(
                    "SELECT rating FROM golf_courses WHERE id = ?", (course_id,)
                ).fetchone()
                price_multiplier = (course_row[0] or 4.0) / 4.0

                for hour, minute in TEE_TIME_HOURS:
                    tee_dt = date.replace(hour=hour, minute=minute)
                    base_price = _get_price(hour, minute)
                    price = round(base_price * price_multiplier, 2)

                    cursor.execute(
                        """
                        INSERT INTO tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player)
                        VALUES (?, ?, 4, 4, ?)
                        """,
                        (course_id, tee_dt.isoformat(), price),
                    )
                    tee_time_count += 1

        print(f"✅ Seeded {len(COURSES)} courses and {tee_time_count} tee times.")


if __name__ == "__main__":
    seed_database()
