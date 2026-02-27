-- Add transcript_segments column to notes table for storing timestamped transcript data
-- This enables transcript highlighting in the iOS app synchronized with audio playback
alter table notes add column if not exists transcript_segments text;
