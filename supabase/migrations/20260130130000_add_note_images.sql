-- Table: note_images
create table if not exists note_images (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users not null,
  note_id uuid references notes(id) on delete cascade,
  remote_url text,
  local_filename text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz
);

-- RLS
alter table note_images enable row level security;

create policy "Users can select own note_images" on note_images for select using (auth.uid() = user_id);
create policy "Users can insert own note_images" on note_images for insert with check (auth.uid() = user_id);
create policy "Users can update own note_images" on note_images for update using (auth.uid() = user_id);
create policy "Users can delete own note_images" on note_images for delete using (auth.uid() = user_id);

