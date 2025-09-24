"""
Audio service for managing audio files and transcriptions with Supabase database.
"""

import uuid
import time
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.core.database import supabase_client
from app.schemas.audio import (
    AudioFileInfo,
    TranscriptionJob,
    AudioTranscriptionResponse,
    AudioUploadResponse
)

logger = logging.getLogger(__name__)


class AudioService:
    """Service for managing audio files and transcriptions."""
    
    def __init__(self):
        self.client = supabase_client.get_service_client()  # Use service client to bypass RLS
        self.logger = logger
    
    async def upload_audio_file(
        self,
        filename: str,
        content_type: str,
        size: int,
        user_id: str = None,
        duration: Optional[float] = None,
        channels: Optional[int] = None,
        sample_rate: Optional[int] = None,
        bit_rate: Optional[int] = None,
        temp_file_path: Optional[str] = None
    ) -> AudioUploadResponse:
        """Upload an audio file to the database."""
        try:
            file_id = str(uuid.uuid4())
            
            # Insert into database
            insert_data = {
                'id': file_id,
                'filename': filename,
                'size': size,
                'content_type': content_type,
                'duration': duration,
                'channels': channels,
                'sample_rate': sample_rate,
                'bit_rate': bit_rate
            }
            
            # For testing, we'll use a different approach
            # Since we can't easily create a user due to foreign key constraints,
            # let's try to use a different strategy
            if not user_id:
                # Try to get any existing user first
                try:
                    existing_user = self.client.table('users').select('id').limit(1).execute()
                    if existing_user.data:
                        user_id = existing_user.data[0]['id']
                    else:
                        # If no users exist, we'll need to handle this differently
                        # Let's try to create a user by bypassing the foreign key constraint
                        # This is a workaround for testing
                        user_id = '00000000-0000-0000-0000-000000000001'
                        
                        # Try to create a user in auth.users first (this might not work)
                        try:
                            # This is a workaround - we'll try to create a user
                            # by using the service client to bypass some constraints
                            user_data = {
                                'id': user_id,
                                'email': 'test@example.com',
                                'full_name': 'Test User'
                            }
                            # Try to insert into users table
                            self.client.table('users').insert(user_data).execute()
                        except Exception as e:
                            # If that fails, we'll need to handle this differently
                            self.logger.warning(f"Could not create test user: {e}")
                            # For now, let's try to use a different approach
                            # We'll need to modify the database schema or use a different strategy
                            raise Exception("No users exist in database and cannot create test user due to foreign key constraints. Please create a user in Supabase dashboard first.")
                except Exception as e:
                    self.logger.error(f"Error handling user_id: {e}")
                    raise Exception(f"Cannot proceed without a valid user_id: {e}")
            
            insert_data['user_id'] = user_id
            
            result = self.client.table('audio_files').insert(insert_data).execute()
            
            if result.data:
                self.logger.info(f"Audio file uploaded: {filename} ({size} bytes)")
                return AudioUploadResponse(
                    file_id=file_id,
                    filename=filename,
                    size=size,
                    content_type=content_type
                )
            else:
                raise Exception("Failed to insert audio file into database")
                
        except Exception as e:
            self.logger.error(f"Failed to upload audio file: {str(e)}")
            raise Exception(f"Upload failed: {str(e)}")
    
    async def create_transcription_job(
        self,
        file_id: str,
        user_id: str = None
    ) -> TranscriptionJob:
        """Create a new transcription job."""
        try:
            job_id = str(uuid.uuid4())
            
            # Insert into database
            result = self.client.table('transcription_jobs').insert({
                'id': job_id,
                'file_id': file_id,
                'status': 'pending',
                'progress': 0.0
            }).execute()
            
            if result.data:
                job = TranscriptionJob(
                    job_id=job_id,
                    file_id=file_id,
                    status="pending",
                    progress=0.0
                )
                
                self.logger.info(f"Transcription job created: {job_id}")
                return job
            else:
                raise Exception("Failed to create transcription job")
                
        except Exception as e:
            self.logger.error(f"Failed to create transcription job: {str(e)}")
            raise Exception(f"Job creation failed: {str(e)}")
    
    async def update_transcription_job(
        self,
        job_id: str,
        status: str,
        progress: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update a transcription job."""
        try:
            update_data = {
                'status': status
            }
            
            if progress is not None:
                update_data['progress'] = progress
            
            if result is not None:
                # Convert result to JSON string for database storage
                if isinstance(result, dict):
                    update_data['result'] = json.dumps(result)
                else:
                    update_data['result'] = result
            
            if error_message is not None:
                update_data['error_message'] = error_message
            
            if status == 'completed':
                update_data['completed_at'] = datetime.utcnow().isoformat()
            
            # Update in database
            self.logger.info(f"Updating job {job_id} with data: {update_data}")
            result = self.client.table('transcription_jobs').update(update_data).eq('id', job_id).execute()
            
            if result.data:
                self.logger.info(f"Transcription job updated: {job_id} - {status}")
                return True
            else:
                self.logger.error(f"Failed to update transcription job {job_id}: {result}")
                raise Exception(f"Failed to update transcription job: {result}")
                
        except Exception as e:
            self.logger.error(f"Failed to update transcription job: {str(e)}")
            return False
    
    async def save_transcription_result(
        self,
        job_id: str,
        transcription_result: AudioTranscriptionResponse
    ) -> bool:
        """Save transcription result to database."""
        try:
            # Save speaker segments
            if transcription_result.segments:
                segments_data = []
                for segment in transcription_result.segments:
                    segments_data.append({
                        'job_id': job_id,
                        'speaker_id': segment.speaker,
                        'start_time': segment.start,
                        'end_time': segment.end,
                        'text': segment.text,
                        'confidence': segment.confidence
                    })
                
                self.client.table('speaker_segments').insert(segments_data).execute()
            
            # Save speaker info
            if transcription_result.speakers:
                speakers_data = []
                for speaker in transcription_result.speakers:
                    speakers_data.append({
                        'job_id': job_id,
                        'speaker_id': speaker.speaker_id,
                        'total_speaking_time': speaker.total_speaking_time,
                        'segment_count': speaker.segment_count,
                        'average_confidence': speaker.average_confidence
                    })
                
                self.client.table('speaker_info').insert(speakers_data).execute()
            
            # Update job with result (exclude datetime fields that can't be JSON serialized)
            result_dict = transcription_result.model_dump(exclude={'created_at'})
            self.logger.info(f"Updating job {job_id} with result: {len(str(result_dict))} characters")
            
            success = await self.update_transcription_job(
                job_id=job_id,
                status='completed',
                progress=100.0,
                result=result_dict
            )
            
            if not success:
                self.logger.error(f"Failed to update job {job_id} status to completed")
                return False
            
            self.logger.info(f"Transcription result saved for job: {job_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save transcription result: {str(e)}")
            return False
    
    async def get_audio_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get audio file information by ID."""
        try:
            result = self.client.table('audio_files').select('*').eq('id', file_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            self.logger.error(f"Failed to get audio file info: {str(e)}")
            return None

    async def get_transcription_job(self, job_id: str, user_id: str = None) -> Optional[TranscriptionJob]:
        """Get a transcription job by ID."""
        try:
            if user_id:
                result = self.client.table('transcription_jobs').select(
                    '*, audio_files!inner(user_id)'
                ).eq('id', job_id).eq('audio_files.user_id', user_id).execute()
            else:
                result = self.client.table('transcription_jobs').select('*').eq('id', job_id).execute()
            
            if result.data:
                job_data = result.data[0]
                # Parse result if it exists
                result_data = None
                if job_data.get('result'):
                    try:
                        if isinstance(job_data['result'], str):
                            result_data = json.loads(job_data['result'])
                        else:
                            result_data = job_data['result']
                    except (json.JSONDecodeError, TypeError):
                        result_data = job_data['result']
                
                return TranscriptionJob(
                    job_id=job_data['id'],
                    file_id=job_data['file_id'],
                    status=job_data['status'],
                    progress=job_data['progress'],
                    result=result_data,
                    error_message=job_data.get('error_message'),
                    created_at=datetime.fromisoformat(job_data['created_at'].replace('Z', '+00:00')),
                    completed_at=datetime.fromisoformat(job_data['completed_at'].replace('Z', '+00:00')) if job_data.get('completed_at') else None
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get transcription job: {str(e)}")
            return None
    
    async def list_transcription_jobs(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TranscriptionJob]:
        """List transcription jobs for a user."""
        try:
            query = self.client.table('transcription_jobs').select(
                '*, audio_files!inner(user_id)'
            ).eq('audio_files.user_id', user_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            
            jobs = []
            for job_data in result.data:
                jobs.append(TranscriptionJob(
                    job_id=job_data['id'],
                    file_id=job_data['file_id'],
                    status=job_data['status'],
                    progress=job_data['progress'],
                    result=job_data.get('result'),
                    error_message=job_data.get('error_message'),
                    created_at=datetime.fromisoformat(job_data['created_at'].replace('Z', '+00:00')),
                    completed_at=datetime.fromisoformat(job_data['completed_at'].replace('Z', '+00:00')) if job_data.get('completed_at') else None
                ))
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Failed to list transcription jobs: {str(e)}")
            return []
    
    async def list_all_transcription_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TranscriptionJob]:
        """List all transcription jobs (for testing without user filtering)."""
        try:
            query = self.client.table('transcription_jobs').select('*')
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            
            jobs = []
            for job_data in result.data:
                # Parse result if it exists
                result_data = None
                if job_data.get('result'):
                    try:
                        if isinstance(job_data['result'], str):
                            result_data = json.loads(job_data['result'])
                        else:
                            result_data = job_data['result']
                    except (json.JSONDecodeError, TypeError):
                        result_data = job_data['result']
                
                jobs.append(TranscriptionJob(
                    job_id=job_data['id'],
                    file_id=job_data['file_id'],
                    status=job_data['status'],
                    progress=job_data['progress'],
                    result=result_data,
                    error_message=job_data.get('error_message'),
                    created_at=datetime.fromisoformat(job_data['created_at'].replace('Z', '+00:00')),
                    completed_at=datetime.fromisoformat(job_data['completed_at'].replace('Z', '+00:00')) if job_data.get('completed_at') else None
                ))
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Failed to list all transcription jobs: {str(e)}")
            return []
    
    async def list_audio_files(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[AudioFileInfo]:
        """List audio files for a user."""
        try:
            result = self.client.table('audio_files').select('*').eq('user_id', user_id).order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            
            files = []
            for file_data in result.data:
                files.append(AudioFileInfo(
                    file_id=file_data['id'],
                    filename=file_data['filename'],
                    size=file_data['size'],
                    content_type=file_data['content_type'],
                    duration=file_data.get('duration'),
                    channels=file_data.get('channels'),
                    sample_rate=file_data.get('sample_rate'),
                    bit_rate=file_data.get('bit_rate'),
                    created_at=datetime.fromisoformat(file_data['created_at'].replace('Z', '+00:00')),
                    user_id=file_data['user_id']
                ))
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list audio files: {str(e)}")
            return []
    
    async def delete_audio_file(self, file_id: str, user_id: str) -> bool:
        """Delete an audio file and related data."""
        try:
            # Delete related transcription jobs first
            self.client.table('transcription_jobs').delete().eq('file_id', file_id).execute()
            
            # Delete the audio file
            result = self.client.table('audio_files').delete().eq('id', file_id).eq('user_id', user_id).execute()
            
            if result.data:
                self.logger.info(f"Audio file deleted: {file_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete audio file: {str(e)}")
            return False