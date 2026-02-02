-- Rename done column to is_completed for consistency with iOS app
alter table todo_items rename column done to is_completed;

-- Add line_index to track position in note content
alter table todo_items add column if not exists line_index integer default 0;

-- Add optional deadline for todos
alter table todo_items add column if not exists deadline timestamptz;
