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
        "name": "Wakasu Golf Links",
        "location": "Koto City, Tokyo",
        "latitude": 35.6177,
        "longitude": 139.8365,
        "holes": 18,
        "par": 72,
        "rating": 4.1,
        "phone": "+81-3-3522-3221",
        "amenities": '["pro_shop", "restaurant", "driving_range", "seaside_views", "rental_clubs"]',
    },
    {
        "name": "Tokyo Kokusai Golf Club",
        "location": "Machida, Tokyo",
        "latitude": 35.6039,
        "longitude": 139.3539,
        "holes": 18,
        "par": 72,
        "rating": 3.8,
        "phone": "+81-42-797-7676",
        "amenities": '["pro_shop", "restaurant", "locker_rooms", "rental_clubs", "practice_green"]',
    },
    {
        "name": "Sakuragaoka Country Club",
        "location": "Tama, Tokyo",
        "latitude": 35.6369,
        "longitude": 139.4468,
        "holes": 18,
        "par": 72,
        "rating": 4.2,
        "phone": "+81-42-375-8811",
        "amenities": '["pro_shop", "restaurant", "clubhouse", "practice_green", "cart_rental"]',
    },
    {
        "name": "Tama Hills Golf Course",
        "location": "Tama, Tokyo",
        "latitude": 35.6238,
        "longitude": 139.4814,
        "holes": 18,
        "par": 72,
        "rating": 4.4,
        "phone": "+81-42-331-1691",
        "amenities": '["pro_shop", "restaurant", "driving_range", "clubhouse", "semi_private_access"]',
    },
    {
        "name": "Sodegaura Country Club",
        "location": "Chiba, Japan",
        "latitude": 35.4293,
        "longitude": 140.0166,
        "holes": 18,
        "par": 72,
        "rating": 4.3,
        "phone": "+81-438-75-5911",
        "amenities": '["pro_shop", "restaurant", "driving_range", "visitors_welcome", "practice_green"]',
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
