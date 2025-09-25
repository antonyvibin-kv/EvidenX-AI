-- Create the media table
CREATE TABLE media (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    media_info JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_media_case_id ON media(case_id);
CREATE INDEX idx_media_media_info ON media USING GIN (media_info);

-- Add comment to document the table
COMMENT ON TABLE media IS 'Media files associated with cases (audio, video, images, documents)';

-- Insert mock media data
INSERT INTO media (id, case_id, media_info) VALUES 
('media1', '1', '{
    "type": "audio",
    "url": "https://evidenx.s3.amazonaws.com/audio/witness_statement_1.mp3",
    "title": "Witness Statement - Security Guard",
    "description": "Audio recording of security guard describing the incident",
    "duration": "08:45",
    "fileSize": "12 MB",
    "format": "mp3",
    "uploadDate": "2024-01-17",
    "transcript": "speaker_0: \"I was on duty at the main entrance when I noticed two individuals acting suspiciously...\"",
    "speakers": 2,
    "confidence": 92
}'),
('media2', '1', '{
    "type": "video",
    "url": "https://evidenx.s3.amazonaws.com/video/cctv_main_entrance.mp4",
    "title": "CCTV Footage - Main Entrance",
    "description": "Security camera footage from main entrance showing suspects entering building",
    "duration": "02:34:15",
    "fileSize": "245 MB",
    "format": "mp4",
    "uploadDate": "2024-01-16",
    "resolution": "1920x1080",
    "fps": 30,
    "thumbnail": "https://evidenx.s3.amazonaws.com/thumbnails/cctv_thumbnail.jpg"
}'),
('media3', '1', '{
    "type": "document",
    "url": "https://evidenx.s3.amazonaws.com/documents/police_report_initial.pdf",
    "title": "Police Report - Initial Investigation",
    "description": "Initial police report with preliminary findings and evidence list",
    "fileSize": "2.3 MB",
    "format": "pdf",
    "uploadDate": "2024-01-15",
    "pages": 5,
    "author": "Inspector Sarah Williams"
}'),
('media4', '1', '{
    "type": "image",
    "url": "https://evidenx.s3.amazonaws.com/images/crime_scene_photo_1.jpg",
    "title": "Crime Scene Photo - Main Counter",
    "description": "Photograph of the main counter area showing evidence markers",
    "fileSize": "8.5 MB",
    "format": "jpg",
    "uploadDate": "2024-01-18",
    "resolution": "4032x3024",
    "camera": "Canon EOS R5",
    "location": "Main Banking Hall"
}'),
('media5', '2', '{
    "type": "audio",
    "url": "https://evidenx.s3.amazonaws.com/audio/accident_witness.mp3",
    "title": "Witness Statement - Accident Victim",
    "description": "Audio recording of accident victim describing the incident",
    "duration": "12:30",
    "fileSize": "15 MB",
    "format": "mp3",
    "uploadDate": "2024-01-20",
    "transcript": "speaker_0: \"I was crossing the street when suddenly a car came speeding towards me...\"",
    "speakers": 1,
    "confidence": 88
}'),
('media6', '2', '{
    "type": "video",
    "url": "https://evidenx.s3.amazonaws.com/video/traffic_camera_incident.mp4",
    "title": "Traffic Camera Footage",
    "description": "Traffic camera footage showing the hit-and-run incident",
    "duration": "01:45:30",
    "fileSize": "180 MB",
    "format": "mp4",
    "uploadDate": "2024-01-20",
    "resolution": "1280x720",
    "fps": 25,
    "location": "Delhi North Intersection"
}');