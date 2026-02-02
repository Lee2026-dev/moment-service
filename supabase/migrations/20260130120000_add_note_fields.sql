-- Add missing fields to notes table
alter table notes add column if not exists title text;
alter table notes add column if not exists is_favorite boolean default false;
alter table notes add column if not exists transcript text;
alter table notes add column if not exists audio_url text;
