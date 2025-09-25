-- Create the cases table
CREATE TABLE cases (
    id TEXT PRIMARY KEY,
    case_info JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create an index on the case_info JSONB column for better query performance
CREATE INDEX idx_cases_case_info ON cases USING GIN (case_info);

-- Insert mock data with proper JSON formatting
INSERT INTO cases (id, case_info) VALUES 
('1', '{
    "firNumber": "FIR/2024/001",
    "title": "Commercial Property Theft Investigation",
    "summary": "Multiple break-ins at commercial complex. CCTV footage and witness testimonies collected. Suspects identified through digital evidence.",
    "petitioner": "Metro Shopping Complex Ltd.",
    "accused": "John Doe, Jane Smith",
    "investigatingOfficer": "Inspector Sarah Williams",
    "registeredDate": "2024-01-15",
    "status": "In-Progress",
    "visibility": "Private",
    "location": "Mumbai Central"
}'),
('2', '{
    "firNumber": "FIR/2024/002",
    "title": "Vehicle Accident Investigation",
    "summary": "Hit-and-run case involving pedestrian injury. Traffic camera footage and mobile phone evidence under analysis.",
    "petitioner": "State Traffic Department",
    "accused": "Unknown Driver",
    "investigatingOfficer": "Sub-Inspector Raj Patel",
    "registeredDate": "2024-01-20",
    "status": "Open",
    "visibility": "Public",
    "location": "Delhi North"
}'),
('3', '{
    "firNumber": "FIR/2024/003",
    "title": "Fraud Investigation - Financial",
    "summary": "Banking fraud involving forged documents and digital manipulation. Multiple witness testimonies recorded.",
    "petitioner": "Union Bank of India",
    "accused": "Michael Johnson",
    "investigatingOfficer": "Inspector Priya Sharma",
    "registeredDate": "2024-02-01",
    "status": "Closed",
    "visibility": "Private",
    "location": "Bangalore Urban"
}');