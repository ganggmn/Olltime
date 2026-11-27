-- 예측 기록표(forecast_log): 수집 함수(api/collect.js)가 5분마다 그때 사이트가 낸 예상을 한 줄씩 남겨요. 2026-11-28 만듦.
-- 지키는 것
--  1) 기록 시각(created_at)은 저장소 시계가 직접 찍어요. 보낸 값은 무시해요.
--  2) 예측 칸 시각(slot_ts)이 지금과 15분 넘게 차이 나면 받지 않아요. 지난 시각의 예상을 나중에 끼워 넣을 수 없어요.
--  3) 줄마다 앞 줄의 지문(prev_hash)을 이어 붙여 sha256 지문(hash)을 만들어요. 한 줄이라도 바뀌면 그 뒤 지문이 모두 어긋나요.
--  4) 고치기(UPDATE)·지우기(DELETE)·비우기(TRUNCATE)는 트리거와 권한 둘 다로 막아요.
--  5) 행 보안(RLS)을 켜고 정책을 두지 않아 공개 키로는 읽지도 쓰지도 못해요(서버 키만).
-- Supabase SQL 편집기에서 한 번 돌려요.

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.forecast_log (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  slot_ts timestamptz not null,
  day date not null,
  model_sha text,
  commit_sha text,
  payload jsonb not null,
  prev_hash text,
  hash text not null default ''
);
alter table public.forecast_log enable row level security;

create or replace function public.forecast_log_chain() returns trigger language plpgsql as $$
declare p text;
begin
  perform pg_advisory_xact_lock(20261128);
  new.created_at := now();
  if abs(extract(epoch from (new.slot_ts - new.created_at))) > 900 then
    raise exception 'forecast_log: slot_ts는 지금과 15분 안이어야 해요';
  end if;
  select f.hash into p from public.forecast_log f order by f.id desc limit 1;
  new.prev_hash := p;
  new.hash := encode(extensions.digest(
    coalesce(p, '') || '|' || new.id::text || '|' ||
    to_char(new.created_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') || '|' ||
    to_char(new.slot_ts at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') || '|' ||
    new.day::text || '|' || coalesce(new.model_sha, '') || '|' || coalesce(new.commit_sha, '') || '|' || new.payload::text, 'sha256'), 'hex');
  return new;
end $$;

create or replace function public.forecast_log_block() returns trigger language plpgsql as $$
begin
  raise exception 'forecast_log: 기록은 고치거나 지울 수 없어요';
end $$;

drop trigger if exists forecast_log_chain on public.forecast_log;
drop trigger if exists forecast_log_no_change on public.forecast_log;
drop trigger if exists forecast_log_no_truncate on public.forecast_log;
create trigger forecast_log_chain before insert on public.forecast_log for each row execute function public.forecast_log_chain();
create trigger forecast_log_no_change before update or delete on public.forecast_log for each row execute function public.forecast_log_block();
create trigger forecast_log_no_truncate before truncate on public.forecast_log for each statement execute function public.forecast_log_block();
revoke update, delete, truncate on public.forecast_log from anon, authenticated, service_role;

-- 확인(누구든 SQL 편집기에서 돌려 볼 수 있음): 모든 줄이 ok·linked = true 여야 해요.
-- select id, created_at, slot_ts,
--   hash = encode(extensions.digest(coalesce(prev_hash, '') || '|' || id::text || '|' ||
--     to_char(created_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') || '|' ||
--     to_char(slot_ts at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') || '|' ||
--     day::text || '|' || coalesce(model_sha, '') || '|' || coalesce(commit_sha, '') || '|' || payload::text, 'sha256'), 'hex') as ok,
--   coalesce(prev_hash = lag(hash) over (order by id), id = (select min(id) from public.forecast_log)) as linked
-- from public.forecast_log order by id;
