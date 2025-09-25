-- Create the case_timeline table
CREATE TABLE case_timeline (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    timeline_info JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_case_timeline_case_id ON case_timeline(case_id);
CREATE INDEX idx_case_timeline_timeline_info ON case_timeline USING GIN (timeline_info);

-- Insert mock timeline data
INSERT INTO case_timeline (id, case_id, timeline_info) VALUES 
('te1', '1', '{
    "timestamp": "2024-01-15T09:00:00Z",
    "title": "Case Registered",
    "description": "FIR filed by Metro Shopping Complex management",
    "source": "case_diary"
}'),
('te2', '1', '{
    "timestamp": "2024-01-15T14:30:00Z",
    "title": "Initial Site Inspection",
    "description": "Crime scene examined, preliminary evidence collected",
    "source": "case_diary"
}'),
('te3', '1', '{
    "timestamp": "2024-01-16T10:15:00Z",
    "title": "CCTV Footage Retrieved",
    "description": "Security camera footage from main entrance collected",
    "evidenceId": "ev1",
    "evidenceType": "video",
    "source": "video"
}'),
('te4', '1', '{
    "timestamp": "2024-01-17T11:00:00Z",
    "title": "Security Guard Interview",
    "description": "Witness statement recorded from on-duty security guard",
    "evidenceId": "ev2",
    "evidenceType": "audio",
    "source": "audio"
}');