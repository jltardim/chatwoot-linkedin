create table if not exists public.dedupe_cache (
  dedupe_key text primary key,
  chat_id text not null,
  normalized_text text not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create index if not exists dedupe_cache_expires_at_idx
  on public.dedupe_cache (expires_at);

create table if not exists public.event_logs (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  source text not null,
  decision text not null,
  chat_id text,
  is_sender boolean,
  message_id text,
  provider_message_id text,
  dedupe_key text,
  normalized_text text,
  payload jsonb,
  error text,
  parse_mode text,
  signature text,
  response jsonb
);

create index if not exists event_logs_created_at_idx
  on public.event_logs (created_at desc);

create index if not exists event_logs_chat_id_idx
  on public.event_logs (chat_id);
