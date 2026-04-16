create index if not exists idx_reservation_history_reservation_id
    on public.reservation_history (reservation_id);

alter view public.course_summaries set (security_invoker = true);
alter view public.tee_time_public set (security_invoker = true);

create or replace view public.reservation_details
with (security_invoker = true) as
select
    r.id,
    r.tee_time_id,
    r.user_id,
    r.num_players,
    r.total_price,
    r.status,
    r.confirmation_number,
    r.hold_expires_at,
    r.created_at,
    r.updated_at,
    c.name as course_name,
    t.tee_datetime,
    u.name as user_name,
    u.email as user_email,
    u.auth_user_id
from public.reservations r
join public.tee_times t on t.id = r.tee_time_id
join public.golf_courses c on c.id = t.course_id
join public.users u on u.id = r.user_id;

grant select on public.reservation_details to authenticated;

drop policy if exists "Users can read own profile" on public.users;
create policy "Users can read own profile"
on public.users
for select
to authenticated
using ((select auth.uid()) = auth_user_id);

drop policy if exists "Users can insert own profile" on public.users;
create policy "Users can insert own profile"
on public.users
for insert
to authenticated
with check ((select auth.uid()) = auth_user_id);

drop policy if exists "Users can update own profile" on public.users;
create policy "Users can update own profile"
on public.users
for update
to authenticated
using ((select auth.uid()) = auth_user_id)
with check ((select auth.uid()) = auth_user_id);

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
          and u.auth_user_id = (select auth.uid())
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
          and u.auth_user_id = (select auth.uid())
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
          and u.auth_user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1
        from public.users u
        where u.id = reservations.user_id
          and u.auth_user_id = (select auth.uid())
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
          and u.auth_user_id = (select auth.uid())
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
          and u.auth_user_id = (select auth.uid())
    )
);

create or replace function public.expire_stale_reservation_holds()
returns void
language plpgsql
set search_path = public
as $$
declare
    stale_row record;
begin
    for stale_row in
        select id, tee_time_id, num_players
        from public.reservations
        where status = 'PENDING'
          and hold_expires_at is not null
          and hold_expires_at < timezone('utc', now())
    loop
        update public.tee_times
        set available_slots = available_slots + stale_row.num_players
        where id = stale_row.tee_time_id;

        insert into public.reservation_history (reservation_id, old_status, new_status, reason)
        values (stale_row.id, 'PENDING', 'EXPIRED', 'Hold expired automatically');
    end loop;

    update public.reservations
    set status = 'EXPIRED',
        updated_at = timezone('utc', now())
    where status = 'PENDING'
      and hold_expires_at is not null
      and hold_expires_at < timezone('utc', now());
end;
$$;

create or replace function public.create_pending_reservation(
    p_tee_time_id bigint,
    p_user_name text,
    p_user_email text,
    p_num_players integer,
    p_user_phone text default null,
    p_auth_user_id uuid default null
)
returns jsonb
language plpgsql
set search_path = public
as $$
declare
    v_tee_time public.tee_times%rowtype;
    v_user_id bigint;
    v_reservation_id bigint;
    v_total_price numeric(10, 2);
    v_reservation jsonb;
begin
    if p_num_players < 1 or p_num_players > 4 then
        return jsonb_build_object('error', 'Number of players must be between 1 and 4.');
    end if;

    perform public.expire_stale_reservation_holds();

    select *
    into v_tee_time
    from public.tee_times
    where id = p_tee_time_id
    for update;

    if not found then
        return jsonb_build_object('error', format('Tee time %s not found.', p_tee_time_id));
    end if;

    if not v_tee_time.is_active then
        return jsonb_build_object('error', 'This tee time is no longer available.');
    end if;

    if v_tee_time.available_slots < p_num_players then
        return jsonb_build_object('error', format('Only %s slots available, but %s requested.', v_tee_time.available_slots, p_num_players));
    end if;

    insert into public.users (auth_user_id, name, email, phone, travel_mode, max_travel_minutes)
    values (p_auth_user_id, p_user_name, p_user_email, p_user_phone, 'train', 60)
    on conflict (email) do update
    set auth_user_id = coalesce(excluded.auth_user_id, public.users.auth_user_id),
        name = excluded.name,
        phone = coalesce(excluded.phone, public.users.phone)
    returning id into v_user_id;

    update public.tee_times
    set available_slots = available_slots - p_num_players
    where id = p_tee_time_id;

    v_total_price := round((v_tee_time.price_per_player * p_num_players)::numeric, 2);

    insert into public.reservations (tee_time_id, user_id, num_players, total_price, status, hold_expires_at)
    values (
        p_tee_time_id,
        v_user_id,
        p_num_players,
        v_total_price,
        'PENDING',
        timezone('utc', now()) + interval '10 minutes'
    )
    returning id into v_reservation_id;

    insert into public.reservation_history (reservation_id, old_status, new_status, reason)
    values (v_reservation_id, null, 'PENDING', 'Reservation created');

    select to_jsonb(rd.*)
    into v_reservation
    from public.reservation_details rd
    where rd.id = v_reservation_id;

    return jsonb_build_object(
        'reservation', v_reservation,
        'message', format(
            'Reservation created! Please confirm within 10 minutes. Booking: %s on %s for %s player(s). Total: JPY %s.',
            v_reservation ->> 'course_name',
            v_reservation ->> 'tee_datetime',
            p_num_players,
            to_char(v_total_price, 'FM999,999,999,990')
        )
    );
end;
$$;

create or replace function public.confirm_pending_reservation(p_reservation_id bigint)
returns jsonb
language plpgsql
set search_path = public
as $$
declare
    v_reservation public.reservations%rowtype;
    v_confirmation_number text;
    v_result jsonb;
begin
    perform public.expire_stale_reservation_holds();

    select *
    into v_reservation
    from public.reservations
    where id = p_reservation_id
    for update;

    if not found then
        return jsonb_build_object('error', format('Reservation %s not found.', p_reservation_id));
    end if;

    if v_reservation.status = 'CONFIRMED' then
        select to_jsonb(rd.*) into v_result from public.reservation_details rd where rd.id = p_reservation_id;
        return jsonb_build_object('error', 'This reservation is already confirmed.', 'reservation', v_result);
    end if;

    if v_reservation.status <> 'PENDING' then
        return jsonb_build_object('error', format('Cannot confirm a reservation with status %s.', v_reservation.status));
    end if;

    if v_reservation.hold_expires_at is not null and v_reservation.hold_expires_at < timezone('utc', now()) then
        return jsonb_build_object('error', 'The hold on this reservation has expired. Please create a new booking.');
    end if;

    v_confirmation_number := format(
        'GR-%s-%s',
        to_char(timezone('utc', now()), 'YYYYMMDD'),
        upper(substr(md5(random()::text || clock_timestamp()::text), 1, 4))
    );

    update public.reservations
    set status = 'CONFIRMED',
        confirmation_number = v_confirmation_number,
        hold_expires_at = null,
        updated_at = timezone('utc', now())
    where id = p_reservation_id;

    insert into public.reservation_history (reservation_id, old_status, new_status, reason)
    values (p_reservation_id, 'PENDING', 'CONFIRMED', 'User confirmed');

    select to_jsonb(rd.*)
    into v_result
    from public.reservation_details rd
    where rd.id = p_reservation_id;

    return jsonb_build_object(
        'reservation', v_result,
        'message', format('Reservation confirmed! Your confirmation number is %s. Enjoy your round at %s!', v_confirmation_number, v_result ->> 'course_name')
    );
end;
$$;

create or replace function public.cancel_existing_reservation(
    p_reservation_id bigint,
    p_reason text default null
)
returns jsonb
language plpgsql
set search_path = public
as $$
declare
    v_reservation public.reservations%rowtype;
    v_result jsonb;
begin
    select *
    into v_reservation
    from public.reservations
    where id = p_reservation_id
    for update;

    if not found then
        return jsonb_build_object('error', format('Reservation %s not found.', p_reservation_id));
    end if;

    if v_reservation.status = 'CANCELLED' then
        return jsonb_build_object('error', 'This reservation is already cancelled.');
    end if;

    if v_reservation.status = 'EXPIRED' then
        return jsonb_build_object('error', 'This reservation has expired and cannot be cancelled.');
    end if;

    update public.reservations
    set status = 'CANCELLED',
        updated_at = timezone('utc', now())
    where id = p_reservation_id;

    update public.tee_times
    set available_slots = available_slots + v_reservation.num_players
    where id = v_reservation.tee_time_id;

    insert into public.reservation_history (reservation_id, old_status, new_status, reason)
    values (p_reservation_id, v_reservation.status, 'CANCELLED', coalesce(p_reason, 'User cancelled'));

    select to_jsonb(rd.*)
    into v_result
    from public.reservation_details rd
    where rd.id = p_reservation_id;

    return jsonb_build_object(
        'reservation', v_result,
        'message', 'Reservation cancelled successfully. The tee time slot has been released.'
    );
end;
$$;

revoke all on function public.expire_stale_reservation_holds() from public, anon, authenticated;
revoke all on function public.create_pending_reservation(bigint, text, text, integer, text, uuid) from public, anon, authenticated;
revoke all on function public.confirm_pending_reservation(bigint) from public, anon, authenticated;
revoke all on function public.cancel_existing_reservation(bigint, text) from public, anon, authenticated;

grant execute on function public.expire_stale_reservation_holds() to service_role;
grant execute on function public.create_pending_reservation(bigint, text, text, integer, text, uuid) to service_role;
grant execute on function public.confirm_pending_reservation(bigint) to service_role;
grant execute on function public.cancel_existing_reservation(bigint, text) to service_role;

insert into public.golf_courses (name, location, latitude, longitude, holes, par, rating, phone, amenities)
select *
from (
    values
        ('Wakasu Golf Links', 'Koto City, Tokyo', 35.6177, 139.8365, 18, 72, 4.1, '+81-3-3522-3221', '["pro_shop", "restaurant", "driving_range", "seaside_views", "rental_clubs"]'::jsonb),
        ('Tokyo Kokusai Golf Club', 'Machida, Tokyo', 35.6039, 139.3539, 18, 72, 3.8, '+81-42-797-7676', '["pro_shop", "restaurant", "locker_rooms", "rental_clubs", "practice_green"]'::jsonb),
        ('Sakuragaoka Country Club', 'Tama, Tokyo', 35.6369, 139.4468, 18, 72, 4.2, '+81-42-375-8811', '["pro_shop", "restaurant", "clubhouse", "practice_green", "cart_rental"]'::jsonb),
        ('Tama Hills Golf Course', 'Tama, Tokyo', 35.6238, 139.4814, 18, 72, 4.4, '+81-42-331-1691', '["pro_shop", "restaurant", "driving_range", "clubhouse", "semi_private_access"]'::jsonb),
        ('Sodegaura Country Club', 'Chiba, Japan', 35.4293, 140.0166, 18, 72, 4.3, '+81-438-75-5911', '["pro_shop", "restaurant", "driving_range", "visitors_welcome", "practice_green"]'::jsonb)
) as seed(name, location, latitude, longitude, holes, par, rating, phone, amenities)
where not exists (select 1 from public.golf_courses);

insert into public.tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player, is_active)
select
    c.id,
    date_trunc('minute', timezone('utc', now()))::date
        + make_interval(days => d.day_offset)
        + make_interval(hours => slot.hour, mins => slot.minute),
    4,
    4,
    round(
        ((
            case
                when (slot.hour * 60 + slot.minute) < 480 then 8500
                when (slot.hour * 60 + slot.minute) < 690 then 15000
                when (slot.hour * 60 + slot.minute) < 840 then 12000
                when (slot.hour * 60 + slot.minute) < 960 then 9500
                else 6500
            end
        )::numeric * coalesce(c.rating, 4.0)::numeric / 4.0),
        2
    ),
    true
from public.golf_courses c
cross join generate_series(0, 29) as d(day_offset)
cross join (
    values
        (6, 0), (6, 30), (7, 0), (7, 30),
        (8, 0), (8, 30), (9, 0), (9, 30),
        (10, 0), (10, 30), (11, 0), (11, 30),
        (12, 0), (12, 30), (13, 0), (13, 30),
        (14, 0), (14, 30), (15, 0), (15, 30),
        (16, 0), (16, 30), (17, 0), (17, 30)
) as slot(hour, minute)
where not exists (select 1 from public.tee_times);
