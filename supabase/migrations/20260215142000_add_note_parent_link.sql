-- Add self-referencing parent note linkage for follow-up voice notes
alter table notes add column if not exists parent_note_id uuid;

-- Keep follow-up links valid and clean up children when parent is removed.
do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'notes_parent_note_id_fkey'
    ) then
        alter table notes
            add constraint notes_parent_note_id_fkey
            foreign key (parent_note_id)
            references notes(id)
            on delete set null;
    end if;
end $$;

-- Prevent a note from referencing itself as parent.
do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'notes_parent_note_not_self_check'
    ) then
        alter table notes
            add constraint notes_parent_note_not_self_check
            check (parent_note_id is null or parent_note_id <> id);
    end if;
end $$;

create index if not exists idx_notes_user_parent_note_id
    on notes(user_id, parent_note_id)
    where deleted_at is null;
