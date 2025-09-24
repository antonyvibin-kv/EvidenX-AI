import asyncio
import time
from typing import Optional, Dict, Any, List
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from deepgram.clients.prerecorded.v1 import PrerecordedResponse
import logging

from app.schemas.audio import (
    AudioTranscriptionRequest,
    AudioTranscriptionResponse,
    SpeakerSegment,
    SpeakerInfo,
    SpeakerDiarizationConfig
)

logger = logging.getLogger(__name__)


class DeepgramService:
    """Service for handling audio transcription with Deepgram."""
    
    def __init__(self, api_key: str):
        """Initialize the Deepgram service."""
        self.client = DeepgramClient(api_key)
        self.logger = logger
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str,
        request: AudioTranscriptionRequest,
        diarization_config: Optional[SpeakerDiarizationConfig] = None
    ) -> AudioTranscriptionResponse:
        """
        Transcribe audio with speaker diarization.
        
        Args:
            audio_data: Raw audio data
            filename: Original filename
            request: Transcription request parameters
            diarization_config: Speaker diarization configuration
            
        Returns:
            AudioTranscriptionResponse with transcript and speaker information
        """
        start_time = time.time()
        
        try:
            # Configure Deepgram options
            options = self._build_transcription_options(request, diarization_config)
            
            # Create file source
            payload: FileSource = {
                "buffer": audio_data,
                "mimetype": self._get_mime_type(filename)
            }
            
            # Perform transcription with timeout handling
            self.logger.info(f"Starting transcription for file: {filename}")
            try:
                response: PrerecordedResponse = self.client.listen.prerecorded.v("1").transcribe_file(
                    payload, options
                )
            except Exception as e:
                if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    self.logger.error(f"Deepgram API timeout for {filename}: {str(e)}")
                    raise Exception(f"Transcription timeout: The audio file may be too large or the network connection is slow. Please try with a smaller file.")
                else:
                    raise e
            
            # Debug: Log response structure
            self.logger.info(f"Deepgram response type: {type(response)}")
            if hasattr(response, 'metadata'):
                self.logger.info(f"Response metadata type: {type(response.metadata)}")
                self.logger.info(f"Response metadata attributes: {dir(response.metadata)}")
            
            # Process the response
            result = self._process_transcription_response(response, start_time)
            
            self.logger.info(f"Transcription completed for {filename} in {result.processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Transcription failed for {filename}: {str(e)}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    def _build_transcription_options(
        self,
        request: AudioTranscriptionRequest,
        diarization_config: Optional[SpeakerDiarizationConfig] = None
    ) -> PrerecordedOptions:
        """Build Deepgram transcription options."""
        options = PrerecordedOptions(
            model=request.model,
            language=request.language,
            punctuate=request.punctuate,
            smart_format=request.smart_format,
            diarize=request.diarize,
            diarize_version="2023-05-22",  # Use latest diarization model
            redact=request.redact or [],
            search=request.search or []
        )
        
        # Add speaker diarization configuration if provided
        if diarization_config and request.diarize:
            options.diarize_version = "2023-05-22"  # Latest diarization model
            options.diarize_min_speakers = diarization_config.min_speakers
            options.diarize_max_speakers = diarization_config.max_speakers
            options.diarize_speaker_change_sensitivity = diarization_config.speaker_change_sensitivity
            options.diarize_speaker_embedding = diarization_config.enable_speaker_embedding
        
        return options
    
    def _process_transcription_response(
        self,
        response: PrerecordedResponse,
        start_time: float
    ) -> AudioTranscriptionResponse:
        """Process Deepgram response into our response format."""
        processing_time = time.time() - start_time
        
        # Extract basic information
        result = response.results
        transcript = result.channels[0].alternatives[0].transcript
        confidence = result.channels[0].alternatives[0].confidence
        
        # Get duration from response metadata
        duration = 0.0
        if hasattr(response, 'metadata') and response.metadata:
            if hasattr(response.metadata, 'duration'):
                duration = response.metadata.duration
            elif hasattr(response.metadata, 'get'):
                duration = response.metadata.get('duration', 0.0)
        
        # Debug: Log the result structure
        self.logger.info(f"Result type: {type(result)}")
        self.logger.info(f"Result attributes: {dir(result)}")
        if hasattr(result, 'utterances'):
            self.logger.info(f"Result.utterances: {result.utterances}")
        else:
            self.logger.info("Result has no utterances attribute")
        
        # Process speaker segments
        segments = []
        speaker_stats = {}
        
        # Access utterances from the response
        utterances = None
        
        # Debug: Log the response structure
        self.logger.info(f"Response type: {type(response)}")
        self.logger.info(f"Response attributes: {dir(response)}")
        
        # Try to access utterances from response.results
        if hasattr(response, 'results') and hasattr(response.results, 'utterances'):
            utterances = response.results.utterances
            self.logger.info(f"Found utterances in response.results: {utterances}")
        elif hasattr(response, 'utterances'):
            utterances = response.utterances
            self.logger.info(f"Found utterances in response: {utterances}")
        else:
            self.logger.info("No utterances found in response")
            
        # If no utterances, try to access from result
        if not utterances and hasattr(result, 'utterances'):
            utterances = result.utterances
            self.logger.info(f"Found utterances in result: {utterances}")
        
        self.logger.info(f"Final utterances: {utterances}")
        
        if utterances:
            for utterance in utterances:
                speaker_id = utterance.speaker
                start_time = utterance.start
                end_time = utterance.end
                text = utterance.transcript
                utterance_confidence = utterance.confidence
                
                # Create speaker segment
                segment = SpeakerSegment(
                    speaker=speaker_id,
                    start=start_time,
                    end=end_time,
                    text=text,
                    confidence=utterance_confidence
                )
                segments.append(segment)
                
                # Update speaker statistics
                if speaker_id not in speaker_stats:
                    speaker_stats[speaker_id] = {
                        'total_time': 0.0,
                        'segment_count': 0,
                        'confidence_sum': 0.0
                    }
                
                speaker_stats[speaker_id]['total_time'] += (end_time - start_time)
                speaker_stats[speaker_id]['segment_count'] += 1
                speaker_stats[speaker_id]['confidence_sum'] += utterance_confidence
        
        # Create speaker information
        speakers = []
        for speaker_id, stats in speaker_stats.items():
            avg_confidence = stats['confidence_sum'] / stats['segment_count'] if stats['segment_count'] > 0 else 0.0
            
            speaker_info = SpeakerInfo(
                speaker_id=speaker_id,
                total_speaking_time=stats['total_time'],
                segment_count=stats['segment_count'],
                average_confidence=avg_confidence
            )
            speakers.append(speaker_info)
        
        # Sort speakers by total speaking time (descending)
        speakers.sort(key=lambda x: x.total_speaking_time, reverse=True)
        
        # Get language from response
        language = "en"  # Default
        if hasattr(result, 'language') and result.language:
            language = result.language
        elif hasattr(response, 'metadata') and response.metadata:
            if hasattr(response.metadata, 'language'):
                language = response.metadata.language
            elif hasattr(response.metadata, 'get'):
                language = response.metadata.get('language', 'en')
        
        return AudioTranscriptionResponse(
            transcript=transcript,
            segments=segments,
            speakers=speakers,
            duration=duration,
            language=language,
            confidence=confidence,
            processing_time=processing_time
        )
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type based on file extension."""
        extension = filename.lower().split('.')[-1]
        mime_types = {
            'wav': 'audio/wav',
            'mp3': 'audio/mpeg',
            'mp4': 'audio/mp4',
            'm4a': 'audio/mp4',
            'flac': 'audio/flac',
            'ogg': 'audio/ogg',
            'webm': 'audio/webm',
            'aac': 'audio/aac',
            'm4b': 'audio/mp4',
            '3gp': 'audio/3gpp',
            'amr': 'audio/amr'
        }
        return mime_types.get(extension, 'audio/wav')
    
    async def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats."""
        return [
            'wav', 'mp3', 'mp4', 'm4a', 'flac', 'ogg', 
            'webm', 'aac', 'm4b', '3gp', 'amr'
        ]
    
    async def validate_audio_file(self, audio_data: bytes, filename: str) -> Dict[str, Any]:
        """Validate audio file before processing."""
        # Check file size (max 2GB for Deepgram, but recommend smaller for better performance)
        max_size = 2 * 1024 * 1024 * 1024  # 2GB
        recommended_size = 50 * 1024 * 1024  # 50MB
        
        if len(audio_data) > max_size:
            raise ValueError(f"File size {len(audio_data)} bytes exceeds maximum size of {max_size} bytes")
        
        if len(audio_data) > recommended_size:
            self.logger.warning(f"Large file detected ({len(audio_data)} bytes). This may cause timeout issues. Consider using a smaller file for better performance.")
        
        # Check file extension
        supported_formats = await self.get_supported_formats()
        extension = filename.lower().split('.')[-1]
        if extension not in supported_formats:
            raise ValueError(f"Unsupported file format: {extension}. Supported formats: {supported_formats}")
        
        # Basic file validation - check if it's not empty
        if len(audio_data) == 0:
            raise ValueError("Audio file is empty")
        
        # Check for common audio file headers
        if extension == 'wav':
            if not audio_data.startswith(b'RIFF'):
                self.logger.warning(f"WAV file {filename} may not have proper RIFF header")
        elif extension == 'mp3':
            if not (audio_data.startswith(b'ID3') or audio_data.startswith(b'\xff\xfb')):
                self.logger.warning(f"MP3 file {filename} may not have proper MP3 header")
        
        return {
            'size': len(audio_data),
            'format': extension,
            'mime_type': self._get_mime_type(filename)
        }