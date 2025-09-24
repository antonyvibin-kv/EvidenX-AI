# EvidenX-AI FastAPI Boilerplate

A production-ready FastAPI boilerplate with Supabase and AWS S3 integration.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **Supabase**: Backend-as-a-Service with PostgreSQL, Authentication, and Storage
- **AWS S3**: File storage and management
- **Authentication**: JWT-based authentication with Supabase Auth
- **File Upload**: Secure file upload to S3 with metadata storage
- **CORS**: Configurable CORS middleware
- **Environment Variables**: Secure configuration management
- **Logging**: Comprehensive logging setup
- **Error Handling**: Global exception handling
- **API Documentation**: Automatic OpenAPI/Swagger documentation

## Project Structure

```
EvidenX-AI/
├── app/
│   ├── api/                    # API routes
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── users.py           # User management endpoints
│   │   └── files.py           # File management endpoints
│   ├── core/                  # Core configuration
│   │   ├── config.py          # Application settings
│   │   ├── database.py        # Supabase client setup
│   │   └── security.py        # Security utilities
│   ├── models/                # Database models
│   ├── schemas/               # Pydantic schemas
│   │   ├── user.py           # User schemas
│   │   └── file.py           # File schemas
│   ├── services/              # Business logic
│   │   ├── s3_service.py     # S3 operations
│   │   └── user_service.py   # User operations
│   ├── utils/                 # Utility functions
│   └── main.py               # FastAPI application
├── tests/                     # Test files
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <your-repo-url>
cd EvidenX-AI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

Required environment variables:

```env
# FastAPI Configuration
APP_NAME="EvidenX-AI API"
APP_VERSION="1.0.0"
DEBUG=True
SECRET_KEY="your-secret-key-here"

# Supabase Configuration
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_KEY="your-supabase-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"

# AWS S3 Configuration
AWS_ACCESS_KEY_ID="your-aws-access-key"
AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
AWS_REGION="us-east-1"
S3_BUCKET_NAME="your-s3-bucket-name"

# CORS Configuration
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8080"
```

### 3. Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Get your project URL and API keys from the project settings
3. Create the following tables in your Supabase database:

```sql
-- Users table (extends Supabase auth.users)
CREATE TABLE public.users (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Files table
CREATE TABLE public.files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    object_name TEXT NOT NULL,
    content_type TEXT,
    size INTEGER,
    url TEXT,
    bucket TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.files ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own files" ON public.files
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own files" ON public.files
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own files" ON public.files
    FOR DELETE USING (auth.uid() = user_id);
```

### 4. AWS S3 Setup

1. Create an S3 bucket in your AWS account
2. Create an IAM user with the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

3. Generate access keys for the IAM user
4. Update your `.env` file with the credentials

### 5. Run the Application

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/logout` - Logout user
- `GET /api/v1/auth/me` - Get current user info

### Users
- `GET /api/v1/users/` - Get all users (admin)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user

### Files
- `POST /api/v1/files/upload` - Upload file to S3
- `GET /api/v1/files/` - Get user's files (paginated)
- `GET /api/v1/files/{file_id}` - Get file metadata
- `GET /api/v1/files/{file_id}/download` - Download file
- `DELETE /api/v1/files/{file_id}` - Delete file

## Usage Examples

### Register a User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "securepassword",
       "full_name": "John Doe"
     }'
```

### Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "securepassword"
     }'
```

### Upload a File
```bash
curl -X POST "http://localhost:8000/api/v1/files/upload" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -F "file=@/path/to/your/file.jpg"
```

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Formatting
```bash
# Install formatting tools
pip install black isort

# Format code
black app/
isort app/
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables for Production
Make sure to set the following in your production environment:
- `DEBUG=False`
- `SECRET_KEY` - Use a strong, random secret key
- `ALLOWED_ORIGINS` - Set to your production domain(s)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

