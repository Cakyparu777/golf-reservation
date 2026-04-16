alter table public.users add column if not exists auth_user_id uuid unique;

create or replace view public.course_summaries as
select
    c.id,
    c.name,
    c.location,
    c.latitude,
    c.longitude,
    c.holes,
    c.par,
    c.rating,
    c.phone,
    c.amenities,
    c.created_at,
    (
        select min(t2.tee_datetime)
        from public.tee_times t2
        where t2.course_id = c.id
          and t2.is_active = true
          and t2.available_slots > 0
          and t2.tee_datetime > timezone('utc', now())
    ) as next_available,
    (
        select min(t3.price_per_player)
        from public.tee_times t3
        where t3.course_id = c.id
          and t3.is_active = true
          and t3.available_slots > 0
          and t3.tee_datetime > timezone('utc', now())
    ) as min_price
from public.golf_courses c;

create or replace view public.tee_time_public as
select
    t.id,
    t.course_id,
    t.tee_datetime,
    t.max_players,
    t.available_slots,
    t.price_per_player,
    t.is_active,
    t.created_at,
    c.name as course_name,
    c.location as course_location
from public.tee_times t
join public.golf_courses c on c.id = t.course_id;

grant select on public.golf_courses to anon, authenticated;
grant select on public.tee_times to anon, authenticated;
grant select on public.course_summaries to anon, authenticated;
grant select on public.tee_time_public to anon, authenticated;
grant select, insert, update on public.users to authenticated;
grant select, insert, update, delete on public.reservations to authenticated;
grant select on public.reservation_history to authenticated;
grant usage, select on sequence public.users_id_seq to authenticated;
grant usage, select on sequence public.reservations_id_seq to authenticated;
grant usage, select on sequence public.reservation_history_id_seq to authenticated;

alter table public.golf_courses enable row level security;
alter table public.tee_times enable row level security;
alter table public.users enable row level security;
alter table public.reservations enable row level security;
alter table public.reservation_history enable row level security;

drop policy if exists "Public read golf courses" on public.golf_courses;
create policy "Public read golf courses"
on public.golf_courses
for select
to anon, authenticated
using (true);

drop policy if exists "Public read tee times" on public.tee_times;
create policy "Public read tee times"
on public.tee_times
for select
to anon, authenticated
using (true);

drop policy if exists "Users can read own profile" on public.users;
create policy "Users can read own profile"
on public.users
for select
to authenticated
using (auth.uid() = auth_user_id);

drop policy if exists "Users can insert own profile" on public.users;
create policy "Users can insert own profile"
on public.users
for insert
to authenticated
with check (auth.uid() = auth_user_id);

drop policy if exists "Users can update own profile" on public.users;
create policy "Users can update own profile"
on public.users
for update
to authenticated
using (auth.uid() = auth_user_id)
with check (auth.uid() = auth_user_id);

drop policy if exists "Users can read own reservations" on public.reservations;
create policy "Users can read own reservations"
on public.reservations
for select
to authenticated
using (
    exists (
        select 1
        from public.users u
        where u.id = reservations.user_id
          and u.auth_user_id = auth.uid()
    )
);

drop policy if exists "Users can create own reservations" on public.reservations;
create policy "Users can create own reservations"
on public.reservations
for insert
to authenticated
with check (
    exists (
        select 1
        from public.users u
        where u.id = reservations.user_id
          and u.auth_user_id = auth.uid()
    )
);

drop policy if exists "Users can update own reservations" on public.reservations;
create policy "Users can update own reservations"
on public.reservations
for update
to authenticated
using (
    exists (
        select 1
        from public.users u
        where u.id = reservations.user_id
          and u.auth_user_id = auth.uid()
    )
)
with check (
    exists (
        select 1
        from public.users u
        where u.id = reservations.user_id
          and u.auth_user_id = auth.uid()
    )
);

drop policy if exists "Users can delete own reservations" on public.reservations;
create policy "Users can delete own reservations"
on public.reservations
for delete
to authenticated
using (
    exists (
        select 1
        from public.users u
        where u.id = reservations.user_id
          and u.auth_user_id = auth.uid()
    )
);

drop policy if exists "Users can read own reservation history" on public.reservation_history;
create policy "Users can read own reservation history"
on public.reservation_history
for select
to authenticated
using (
    exists (
        select 1
        from public.reservations r
        join public.users u on u.id = r.user_id
        where r.id = reservation_history.reservation_id
          and u.auth_user_id = auth.uid()
    )
);
