-- Add S3 key column to audio_files table
ALTER TABLE audio_files ADD COLUMN s3_key TEXT;

-- Create index on s3_key for better query performance
CREATE INDEX idx_audio_files_s3_key ON audio_files(s3_key);

-- Add comment to document the new column
COMMENT ON COLUMN audio_files.s3_key IS 'S3 object key for the uploaded audio file';