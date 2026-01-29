-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Table: notes
create table notes (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users not null,
  content text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz
);

-- Table: tags
create table tags (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users not null,
  name text not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz
);

-- Table: todo_items
create table todo_items (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users not null,
  note_id uuid references notes(id),
  text text not null,
  done boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz
);

-- Table: user_devices (for FCM)
create table user_devices (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid references auth.users not null,
    fcm_token text not null,
    created_at timestamptz default now(),
    updated_at timestamptz default now(),
    unique(user_id, fcm_token)
);

-- Enable RLS
alter table notes enable row level security;
alter table tags enable row level security;
alter table todo_items enable row level security;
alter table user_devices enable row level security;

-- Policies: Notes
create policy "Users can select own notes" on notes for select using (auth.uid() = user_id);
create policy "Users can insert own notes" on notes for insert with check (auth.uid() = user_id);
create policy "Users can update own notes" on notes for update using (auth.uid() = user_id);
create policy "Users can delete own notes" on notes for delete using (auth.uid() = user_id);

-- Policies: Tags
create policy "Users can select own tags" on tags for select using (auth.uid() = user_id);
create policy "Users can insert own tags" on tags for insert with check (auth.uid() = user_id);
create policy "Users can update own tags" on tags for update using (auth.uid() = user_id);
create policy "Users can delete own tags" on tags for delete using (auth.uid() = user_id);

-- Policies: TodoItems
create policy "Users can select own todo_items" on todo_items for select using (auth.uid() = user_id);
create policy "Users can insert own todo_items" on todo_items for insert with check (auth.uid() = user_id);
create policy "Users can update own todo_items" on todo_items for update using (auth.uid() = user_id);
create policy "Users can delete own todo_items" on todo_items for delete using (auth.uid() = user_id);

-- Policies: UserDevices
create policy "Users can select own devices" on user_devices for select using (auth.uid() = user_id);
create policy "Users can insert own devices" on user_devices for insert with check (auth.uid() = user_id);
create policy "Users can update own devices" on user_devices for update using (auth.uid() = user_id);
create policy "Users can delete own devices" on user_devices for delete using (auth.uid() = user_id);
