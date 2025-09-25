-- Create the case_timeline table (if not exists)
CREATE TABLE IF NOT EXISTS case_timeline (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    timeline_info JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_case_timeline_case_id ON case_timeline(case_id);
CREATE INDEX IF NOT EXISTS idx_case_timeline_timeline_info ON case_timeline USING GIN (timeline_info);

-- Clear existing data
DELETE FROM case_timeline WHERE case_id = '1';

-- Insert new timeline data with the updated format
INSERT INTO case_timeline (id, case_id, timeline_info) VALUES 
('1', '1', '{
    "id": 1,
    "time": 14.0,
    "duration": 2.0,
    "actor": "suspect1",
    "date": {"day": 28, "month": 3},
    "title": "Bank surveillance begins",
    "type": "video",
    "confidence": 85,
    "evidence": "CCTV Camera #3 - Exterior",
    "description": "Suspect A observed studying bank layout and security patterns"
}'),
('2', '1', '{
    "id": 2,
    "time": 16.5,
    "duration": 0.5,
    "actor": "suspect2",
    "date": {"day": 28, "month": 3},
    "title": "Vehicle reconnaissance",
    "type": "video",
    "confidence": 78,
    "evidence": "Traffic Camera #12",
    "description": "Red sedan circles block multiple times, license partially obscured"
}'),
('3', '1', '{
    "id": 3,
    "time": 11.0,
    "duration": 1.0,
    "actor": "suspect1",
    "date": {"day": 31, "month": 3},
    "title": "Suspects meet at location",
    "type": "witness",
    "confidence": 82,
    "evidence": "Witness Statement #1",
    "description": "Two individuals seen meeting at nearby café, appeared to be planning"
}'),
('4', '1', '{
    "id": 4,
    "time": 15.0,
    "duration": 0.3,
    "actor": "suspect2",
    "date": {"day": 31, "month": 3},
    "title": "Equipment acquisition",
    "type": "video",
    "confidence": 90,
    "evidence": "Store CCTV #5",
    "description": "Purchase of masks and tools from hardware store"
}'),
('5', '1', '{
    "id": 5,
    "time": 8.5,
    "duration": 0.5,
    "actor": "suspect1",
    "date": {"day": 1, "month": 4},
    "title": "Suspect A arrives at bank area",
    "type": "video",
    "confidence": 95,
    "evidence": "CCTV Camera #3 - Exterior",
    "description": "Individual in blue jacket observed loitering near bank entrance"
}'),
('6', '1', '{
    "id": 6,
    "time": 8.7,
    "duration": 0.3,
    "actor": "suspect2",
    "date": {"day": 1, "month": 4},
    "title": "Getaway vehicle positioned",
    "type": "video",
    "confidence": 87,
    "evidence": "CCTV Camera #1 - Parking",
    "description": "Red sedan parks in optimal escape position"
}'),
('7', '1', '{
    "id": 7,
    "time": 9.2,
    "duration": 0.8,
    "actor": "suspect1",
    "date": {"day": 1, "month": 4},
    "title": "Bank entry - robbery begins",
    "type": "video",
    "confidence": 98,
    "evidence": "CCTV Camera #5 - Entrance",
    "description": "Suspect enters bank, face covered, weapon visible"
}'),
('8', '1', '{
    "id": 8,
    "time": 9.3,
    "duration": 0.3,
    "actor": "victim1",
    "date": {"day": 1, "month": 4},
    "title": "Silent alarm activated",
    "type": "location",
    "confidence": 100,
    "evidence": "Security System Log",
    "description": "Bank teller triggers panic button under duress"
}'),
('9', '1', '{
    "id": 9,
    "time": 9.5,
    "duration": 2.0,
    "actor": "witness2",
    "date": {"day": 1, "month": 4},
    "title": "Emergency response call",
    "type": "audio",
    "confidence": 92,
    "evidence": "911 Call Recording #447",
    "description": "Security guard reports robbery in progress"
}'),
('10', '1', '{
    "id": 10,
    "time": 10.0,
    "duration": 0.5,
    "actor": "suspect1",
    "date": {"day": 1, "month": 4},
    "title": "Cash obtained and exit",
    "type": "video",
    "confidence": 95,
    "evidence": "CCTV Camera #6 - Counter",
    "description": "Suspect receives money bag, exits through main entrance"
}'),
('11', '1', '{
    "id": 11,
    "time": 10.2,
    "duration": 0.2,
    "actor": "suspect2",
    "date": {"day": 1, "month": 4},
    "title": "Escape vehicle departure",
    "type": "video",
    "confidence": 90,
    "evidence": "CCTV Camera #1 - Parking",
    "description": "Red sedan speeds away from scene"
}'),
('12', '1', '{
    "id": 12,
    "time": 9.0,
    "duration": 1.0,
    "actor": "witness1",
    "date": {"day": 2, "month": 4},
    "title": "Witness comes forward",
    "type": "witness",
    "confidence": 88,
    "evidence": "Witness Statement #2",
    "description": "Customer provides detailed description of suspects and vehicle"
}'),
('13', '1', '{
    "id": 13,
    "time": 14.0,
    "duration": 0.5,
    "actor": "location1",
    "date": {"day": 2, "month": 4},
    "title": "Evidence collection",
    "type": "location",
    "confidence": 95,
    "evidence": "Forensic Report #1",
    "description": "Fingerprints and DNA evidence recovered from bank counter"
}'),
('14', '1', '{
    "id": 14,
    "time": 16.0,
    "duration": 1.5,
    "actor": "suspect2",
    "date": {"day": 2, "month": 4},
    "title": "Vehicle abandonment",
    "type": "video",
    "confidence": 92,
    "evidence": "CCTV Camera #8 - Industrial Area",
    "description": "Red sedan found abandoned, forensic team deployed"
}');