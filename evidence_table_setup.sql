-- Create the evidence table
CREATE TABLE evidence (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    evidence_info JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_evidence_case_id ON evidence(case_id);
CREATE INDEX idx_evidence_evidence_info ON evidence USING GIN (evidence_info);

-- Insert mock evidence data
INSERT INTO evidence (id, case_id, evidence_info) VALUES 
('ev1', '1', '{
    "type": "video",
    "name": "CCTV Footage - Main Entrance",
    "description": "Security camera footage from main entrance showing suspects entering building",
    "uploadDate": "2024-01-16",
    "fileSize": "245 MB",
    "tags": ["surveillance", "suspects", "entrance"],
    "duration": "02:34:15",
    "thumbnail": "https://images.unsplash.com/photo-1734812070354-a0af3c243b2a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxwb2xpY2UlMjBpbnZlc3RpZ2F0aW9uJTIwZXZpZGVuY2V8ZW58MXx8fHwxNzU4NjkzMzM2fDA&ixlib=rb-4.1.0&q=80&w=1080"
}'),
('ev2', '1', '{
    "type": "audio",
    "name": "Witness Statement - Security Guard",
    "description": "Audio recording of security guard describing the incident",
    "uploadDate": "2024-01-17",
    "fileSize": "12 MB",
    "tags": ["witness", "testimony", "security"],
    "duration": "08:45"
}'),
('ev3', '1', '{
    "type": "document",
    "name": "Police Report - Initial Investigation",
    "description": "Initial police report with preliminary findings and evidence list",
    "uploadDate": "2024-01-15",
    "fileSize": "2.3 MB",
    "tags": ["official", "preliminary", "report"],
    "thumbnail": "https://images.unsplash.com/photo-1731074803846-ac506947040d?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxsYXclMjBlbmZvcmNlbWVudCUyMGRvY3VtZW50JTIwZmlsZXN8ZW58MXx8fHwxNzU4NjkzMzQwfDA&ixlib=rb-4.1.0&q=80&w=1080"
}'),
('ev4', '1', '{
    "type": "audio",
    "name": "Witness Statement - Store Owner",
    "description": "Audio recording of store owner testimony about the incident",
    "uploadDate": "2024-01-18",
    "fileSize": "15 MB",
    "tags": ["witness", "testimony", "victim"],
    "duration": "12:30"
}');