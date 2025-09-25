-- Add new columns to audio_files table for analyze functionality
ALTER TABLE audio_files ADD COLUMN IF NOT EXISTS case_id TEXT;
ALTER TABLE audio_files ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE audio_files ADD COLUMN IF NOT EXISTS audio_info JSONB;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_audio_files_case_id ON audio_files(case_id);
CREATE INDEX IF NOT EXISTS idx_audio_files_url ON audio_files(url);
CREATE INDEX IF NOT EXISTS idx_audio_files_audio_info ON audio_files USING GIN (audio_info);

-- Add foreign key constraint for case_id
ALTER TABLE audio_files ADD CONSTRAINT fk_audio_files_case_id 
FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE;

-- Add comments to document the new columns
COMMENT ON COLUMN audio_files.case_id IS 'Case identifier for grouping audio files';
COMMENT ON COLUMN audio_files.url IS 'URL of the audio file (S3 or external)';
COMMENT ON COLUMN audio_files.audio_info IS 'JSON containing transcript and follow-up questions from AI analysis';