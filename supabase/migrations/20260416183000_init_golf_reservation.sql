create table if not exists public.golf_courses (
    id bigserial primary key,
    name text not null,
    location text not null,
    latitude double precision,
    longitude double precision,
    holes integer not null default 18,
    par integer,
    rating double precision,
    phone text,
    amenities jsonb,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.tee_times (
    id bigserial primary key,
    course_id bigint not null references public.golf_courses(id) on delete cascade,
    tee_datetime timestamptz not null,
    max_players integer not null default 4,
    available_slots integer not null,
    price_per_player numeric(10, 2) not null,
    is_active boolean not null default true,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.users (
    id bigserial primary key,
    name text not null,
    email text not null unique,
    phone text,
    home_area text,
    travel_mode text not null default 'train',
    max_travel_minutes integer not null default 60,
    password_hash text,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.reservations (
    id bigserial primary key,
    tee_time_id bigint not null references public.tee_times(id) on delete cascade,
    user_id bigint not null references public.users(id) on delete cascade,
    num_players integer not null check (num_players between 1 and 4),
    total_price numeric(10, 2) not null,
    status text not null default 'PENDING',
    confirmation_number text unique,
    hold_expires_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.reservation_history (
    id bigserial primary key,
    reservation_id bigint not null references public.reservations(id) on delete cascade,
    old_status text,
    new_status text not null,
    reason text,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_tee_times_course_date on public.tee_times (course_id, tee_datetime);
create index if not exists idx_tee_times_datetime on public.tee_times (tee_datetime);
create index if not exists idx_reservations_user on public.reservations (user_id);
create index if not exists idx_reservations_tee_time on public.reservations (tee_time_id);
create index if not exists idx_reservations_status on public.reservations (status);
create index if not exists idx_users_email on public.users (email);
