-- Per-user AI feature usage counters
create table if not exists user_ai_stats (
  user_id uuid primary key references auth.users not null,
  summarize_count bigint not null default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table user_ai_stats enable row level security;

create policy "Users can select own ai stats"
on user_ai_stats for select
using (auth.uid() = user_id);

create policy "Users can insert own ai stats"
on user_ai_stats for insert
with check (auth.uid() = user_id);

create policy "Users can update own ai stats"
on user_ai_stats for update
using (auth.uid() = user_id);
