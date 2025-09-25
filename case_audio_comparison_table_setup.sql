-- Create the case_audio_comparison table
CREATE TABLE case_audio_comparison (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    media_id1 TEXT NOT NULL,
    media_id2 TEXT NOT NULL,
    witnesses JSONB NOT NULL,
    detailed_analysis JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_case_audio_comparison_case_id ON case_audio_comparison(case_id);
CREATE INDEX idx_case_audio_comparison_media_ids ON case_audio_comparison(media_id1, media_id2);
CREATE INDEX idx_case_audio_comparison_witnesses ON case_audio_comparison USING GIN (witnesses);
CREATE INDEX idx_case_audio_comparison_detailed_analysis ON case_audio_comparison USING GIN (detailed_analysis);

-- Add comment to document the table
COMMENT ON TABLE case_audio_comparison IS 'Audio comparison analysis between two media files in a case';

-- Insert mock audio comparison data
INSERT INTO case_audio_comparison (id, case_id, media_id1, media_id2, witnesses, detailed_analysis) VALUES 
('ac1', '1', 'ev2', 'ev4', '[
  {
    "id": "ac1",
    "witnessName": "Rajesh Kumar (Security Guard)",
    "witnessImage": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face",
    "audioId": "ev2",
    "summary": "Security guard describes seeing two individuals enter through main entrance around 2:30 AM. Mentions suspicious behavior and unfamiliar faces.",
    "transcript": "I was on duty that night when I saw two people coming through the main gate. They looked suspicious, wearing dark clothes and caps. I tried to question them but they rushed inside.",
    "contradictions": ["Time mentioned differs from CCTV timestamp"],
    "similarities": ["Confirms two suspects", "Dark clothing description matches video"],
    "grayAreas": ["Unclear about exact location of entry"]
  },
  {
    "id": "ac2",
    "witnessName": "Meera Patel (Store Owner)",
    "witnessImage": "https://images.unsplash.com/photo-1494790108755-2616b2abff16?w=150&h=150&fit=crop&crop=face",
    "audioId": "ev4",
    "summary": "Store owner discovered the break-in next morning. Describes missing inventory and damaged property. Provides details about security arrangements.",
    "transcript": "When I arrived at 9 AM, I found the lock broken and items missing from the store. The cash register was tampered with and several electronic items were gone.",
    "contradictions": ["Claims to have CCTV inside store but no footage found"],
    "similarities": ["Confirms break-in occurred overnight", "Missing items match reported theft"],
    "grayAreas": ["Uncertain about exact time of discovery"]
  }
]', '[
  {
    "topic": "Time of incident",
    "witness1": "Around 2:30 AM",
    "witness2": "Approximately 2:15 AM",
    "status": "contradiction",
    "details": "15-minute discrepancy in reported time"
  },
  {
    "topic": "Number of suspects",
    "witness1": "Two individuals",
    "witness2": "Two people",
    "status": "similarity",
    "details": "Both witnesses consistently report two suspects"
  },
  {
    "topic": "Suspect clothing",
    "witness1": "Dark clothes and caps",
    "witness2": "Dark attire, couldn''t see faces clearly",
    "status": "similarity",
    "details": "Consistent description of dark clothing"
  },
  {
    "topic": "Suspect behavior",
    "witness1": "Rushing, avoiding lights",
    "witness2": "Seemed in hurry, furtive movements",
    "status": "similarity",
    "details": "Both describe suspicious, hurried behavior"
  },
  {
    "topic": "Items carried",
    "witness1": "One person carrying something",
    "witness2": "Noticed bag or tools",
    "status": "gray_area",
    "details": "Similar observation but unclear specifics"
  },
  {
    "topic": "Exit observation",
    "witness1": "Didn''t see them leave",
    "witness2": "Not mentioned",
    "status": "gray_area",
    "details": "Incomplete information about suspects'' departure"
  }
]');