"""SQL query constants.

All raw SQL lives here so tool modules stay focused on business logic.
Queries use named placeholders (:param) for clarity and safety.
"""

# ---------------------------------------------------------------------------
# Schema Creation
# ---------------------------------------------------------------------------

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS golf_courses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    location    TEXT    NOT NULL,
    latitude    REAL,
    longitude   REAL,
    holes       INTEGER DEFAULT 18,
    par         INTEGER,
    rating      REAL,
    phone       TEXT,
    amenities   TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tee_times (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id         INTEGER NOT NULL REFERENCES golf_courses(id),
    tee_datetime      TEXT    NOT NULL,
    max_players       INTEGER DEFAULT 4,
    available_slots   INTEGER NOT NULL,
    price_per_player  REAL    NOT NULL,
    is_active         INTEGER DEFAULT 1,
    created_at        TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    phone         TEXT,
    password_hash TEXT,
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reservations (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    tee_time_id          INTEGER NOT NULL REFERENCES tee_times(id),
    user_id              INTEGER NOT NULL REFERENCES users(id),
    num_players          INTEGER NOT NULL CHECK (num_players BETWEEN 1 AND 4),
    total_price          REAL    NOT NULL,
    status               TEXT    NOT NULL DEFAULT 'PENDING',
    confirmation_number  TEXT    UNIQUE,
    hold_expires_at      TEXT,
    created_at           TEXT    DEFAULT (datetime('now')),
    updated_at           TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reservation_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id  INTEGER NOT NULL REFERENCES reservations(id),
    old_status      TEXT,
    new_status      TEXT    NOT NULL,
    reason          TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tee_times_course_date
    ON tee_times(course_id, tee_datetime);

CREATE INDEX IF NOT EXISTS idx_tee_times_datetime
    ON tee_times(tee_datetime);

CREATE INDEX IF NOT EXISTS idx_reservations_user
    ON reservations(user_id);

CREATE INDEX IF NOT EXISTS idx_reservations_tee_time
    ON reservations(tee_time_id);

CREATE INDEX IF NOT EXISTS idx_reservations_status
    ON reservations(status);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email);
"""

# ---------------------------------------------------------------------------
# Search Queries
# ---------------------------------------------------------------------------

SEARCH_TEE_TIMES = """
SELECT
    t.id,
    t.course_id,
    t.tee_datetime,
    t.max_players,
    t.available_slots,
    t.price_per_player,
    t.is_active,
    t.created_at,
    c.name  AS course_name,
    c.location AS course_location
FROM tee_times t
JOIN golf_courses c ON t.course_id = c.id
WHERE t.is_active = 1
  AND t.available_slots >= :num_players
  AND date(t.tee_datetime) = :date
  AND time(t.tee_datetime) >= :time_start
  AND time(t.tee_datetime) <= :time_end
  {course_filter}
ORDER BY t.tee_datetime ASC
LIMIT 20
"""

SEARCH_TEE_TIMES_COURSE_FILTER = "AND c.name LIKE :course_name"

GET_COURSE_BY_ID = """
SELECT * FROM golf_courses WHERE id = :course_id
"""

GET_COURSE_BY_NAME = """
SELECT * FROM golf_courses WHERE name LIKE :course_name
"""

# ---------------------------------------------------------------------------
# Alternative Suggestions
# ---------------------------------------------------------------------------

NEARBY_COURSES = """
SELECT
    t.id,
    t.course_id,
    t.tee_datetime,
    t.max_players,
    t.available_slots,
    t.price_per_player,
    t.is_active,
    t.created_at,
    c.name  AS course_name,
    c.location AS course_location,
    (
        (c.latitude - :lat) * (c.latitude - :lat) +
        (c.longitude - :lng) * (c.longitude - :lng)
    ) AS distance_sq
FROM tee_times t
JOIN golf_courses c ON t.course_id = c.id
WHERE t.is_active = 1
  AND t.available_slots >= :num_players
  AND date(t.tee_datetime) = :date
  AND time(t.tee_datetime) >= :time_start
  AND time(t.tee_datetime) <= :time_end
  AND c.latitude IS NOT NULL
  AND c.longitude IS NOT NULL
ORDER BY distance_sq ASC
LIMIT 10
"""

ALTERNATIVE_TIMES = """
SELECT
    t.id,
    t.course_id,
    t.tee_datetime,
    t.max_players,
    t.available_slots,
    t.price_per_player,
    t.is_active,
    t.created_at,
    c.name  AS course_name,
    c.location AS course_location
FROM tee_times t
JOIN golf_courses c ON t.course_id = c.id
WHERE t.is_active = 1
  AND t.available_slots >= :num_players
  AND c.name LIKE :course_name
  AND date(t.tee_datetime) BETWEEN date(:date, '-1 day') AND date(:date, '+1 day')
  AND NOT (date(t.tee_datetime) = :date
           AND time(t.tee_datetime) >= :time_start
           AND time(t.tee_datetime) <= :time_end)
ORDER BY ABS(julianday(t.tee_datetime) - julianday(:date || 'T' || :time_start)) ASC
LIMIT 10
"""

# ---------------------------------------------------------------------------
# Reservation Queries
# ---------------------------------------------------------------------------

GET_TEE_TIME_BY_ID = """
SELECT
    t.*,
    c.name AS course_name,
    c.location AS course_location
FROM tee_times t
JOIN golf_courses c ON t.course_id = c.id
WHERE t.id = :tee_time_id
"""

INSERT_USER = """
INSERT INTO users (name, email, phone)
VALUES (:name, :email, :phone)
ON CONFLICT(email) DO UPDATE SET
    name = excluded.name,
    phone = COALESCE(excluded.phone, users.phone)
"""

GET_USER_BY_EMAIL = """
SELECT * FROM users WHERE email = :email
"""

INSERT_RESERVATION = """
INSERT INTO reservations (tee_time_id, user_id, num_players, total_price, status, hold_expires_at)
VALUES (:tee_time_id, :user_id, :num_players, :total_price, 'PENDING', :hold_expires_at)
"""

DECREMENT_AVAILABLE_SLOTS = """
UPDATE tee_times
SET available_slots = available_slots - :num_players
WHERE id = :tee_time_id
  AND available_slots >= :num_players
"""

GET_RESERVATION_BY_ID = """
SELECT
    r.*,
    c.name AS course_name,
    t.tee_datetime,
    u.name AS user_name,
    u.email AS user_email
FROM reservations r
JOIN tee_times t ON r.tee_time_id = t.id
JOIN golf_courses c ON t.course_id = c.id
JOIN users u ON r.user_id = u.id
WHERE r.id = :reservation_id
"""

CONFIRM_RESERVATION = """
UPDATE reservations
SET status = 'CONFIRMED',
    confirmation_number = :confirmation_number,
    hold_expires_at = NULL,
    updated_at = datetime('now')
WHERE id = :reservation_id
  AND status = 'PENDING'
"""

CANCEL_RESERVATION = """
UPDATE reservations
SET status = 'CANCELLED',
    updated_at = datetime('now')
WHERE id = :reservation_id
  AND status IN ('PENDING', 'CONFIRMED')
"""

RESTORE_AVAILABLE_SLOTS = """
UPDATE tee_times
SET available_slots = available_slots + :num_players
WHERE id = :tee_time_id
"""

INSERT_HISTORY = """
INSERT INTO reservation_history (reservation_id, old_status, new_status, reason)
VALUES (:reservation_id, :old_status, :new_status, :reason)
"""

# ---------------------------------------------------------------------------
# User Queries
# ---------------------------------------------------------------------------

LIST_USER_RESERVATIONS = """
SELECT
    r.*,
    c.name AS course_name,
    t.tee_datetime,
    u.name AS user_name,
    u.email AS user_email
FROM reservations r
JOIN tee_times t ON r.tee_time_id = t.id
JOIN golf_courses c ON t.course_id = c.id
JOIN users u ON r.user_id = u.id
WHERE u.email = :email
  {status_filter}
ORDER BY t.tee_datetime DESC
LIMIT 50
"""

LIST_USER_RESERVATIONS_STATUS_FILTER = "AND r.status = :status"

# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

EXPIRE_STALE_HOLDS = """
UPDATE reservations
SET status = 'EXPIRED',
    updated_at = datetime('now')
WHERE status = 'PENDING'
  AND hold_expires_at < datetime('now')
"""

# ---------------------------------------------------------------------------
# Auth / API Queries
# ---------------------------------------------------------------------------

INSERT_USER_AUTH = """
INSERT INTO users (name, email, phone, password_hash)
VALUES (:name, :email, :phone, :password_hash)
"""

GET_USER_BY_ID = """
SELECT * FROM users WHERE id = :user_id
"""

LIST_COURSES = """
SELECT
    c.*,
    (
        SELECT MIN(t2.tee_datetime)
        FROM tee_times t2
        WHERE t2.course_id = c.id
          AND t2.is_active = 1
          AND t2.available_slots > 0
          AND datetime(t2.tee_datetime) > datetime('now')
    ) AS next_available,
    (
        SELECT MIN(t3.price_per_player)
        FROM tee_times t3
        WHERE t3.course_id = c.id
          AND t3.is_active = 1
          AND t3.available_slots > 0
          AND datetime(t3.tee_datetime) > datetime('now')
    ) AS min_price
FROM golf_courses c
ORDER BY c.rating DESC
"""

API_SEARCH_TEE_TIMES = """
SELECT
    t.*,
    c.name AS course_name,
    c.location AS course_location
FROM tee_times t
JOIN golf_courses c ON t.course_id = c.id
WHERE t.is_active = 1
  AND t.available_slots >= :num_players
  AND datetime(t.tee_datetime) > datetime('now')
ORDER BY t.tee_datetime ASC
LIMIT :limit
"""

API_SEARCH_TEE_TIMES_BY_COURSE = """
SELECT
    t.*,
    c.name AS course_name,
    c.location AS course_location
FROM tee_times t
JOIN golf_courses c ON t.course_id = c.id
WHERE t.is_active = 1
  AND t.available_slots >= :num_players
  AND t.course_id = :course_id
  AND datetime(t.tee_datetime) > datetime('now')
ORDER BY t.tee_datetime ASC
LIMIT :limit
"""
