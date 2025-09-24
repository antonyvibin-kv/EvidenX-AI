import asyncio
import time
import httpx
import json
from typing import Optional, Dict, Any, List
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
        self.api_key = api_key
        self.base_url = "https://api.deepgram.com/v1/listen"
        self.logger = logger
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str,
        request: AudioTranscriptionRequest,
        diarization_config: Optional[SpeakerDiarizationConfig] = None
    ) -> AudioTranscriptionResponse:
        """
        Transcribe audio with speaker diarization using direct HTTP calls.
        
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
            # Build query parameters
            params = self._build_query_params(request, diarization_config)
            
            # Prepare headers
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": self._get_mime_type(filename)
            }
            
            # Perform transcription with timeout handling
            self.logger.info(f"Starting transcription for file: {filename}")
            self.logger.info(f"Using URL: {self.base_url}")
            self.logger.info(f"Query params: {params}")
            
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(
                        self.base_url,
                        params=params,
                        headers=headers,
                        content=audio_data
                    )
                    print("--------------------------------")
                    print(response)
                    print("--------------------------------")
                    
                    if response.status_code != 200:
                        raise Exception(f"Deepgram API error: {response.status_code} - {response.text}")
                    
                    response_data = response.json()
                    print("--------------------------------")
                    print(response_data)
                    print("--------------------------------")
                    self.logger.info(f"Deepgram response received: {len(str(response_data))} characters")
                    
            except httpx.TimeoutException:
                self.logger.error(f"Deepgram API timeout for {filename}")
                raise Exception(f"Transcription timeout: The audio file may be too large or the network connection is slow. Please try with a smaller file.")
            except Exception as e:
                self.logger.error(f"HTTP request failed: {str(e)}")
                raise e
            
            # Process the response
            result = self._process_transcription_response(response_data, start_time)
            
            self.logger.info(f"Transcription completed for {filename} in {result.processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Transcription failed for {filename}: {str(e)}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    def _build_query_params(
        self,
        request: AudioTranscriptionRequest,
        diarization_config: Optional[SpeakerDiarizationConfig] = None
    ) -> Dict[str, Any]:
        """Build query parameters for Deepgram API."""
        params = {
            "model": "nova-2",  # Use nova-2 to match your working Postman call
            "language": request.language,
            "punctuate": str(request.punctuate).lower(),
            "smart_format": str(request.smart_format).lower(),
            "diarize": str(request.diarize).lower()
        }
        
        # Add optional parameters
        if request.redact:
            params["redact"] = ",".join(request.redact)
        if request.search:
            params["search"] = ",".join(request.search)
        
        # Add speaker diarization configuration if provided
        if diarization_config and request.diarize:
            params["diarize_min_speakers"] = str(diarization_config.min_speakers)
            params["diarize_max_speakers"] = str(diarization_config.max_speakers)
            params["diarize_speaker_change_sensitivity"] = str(diarization_config.speaker_change_sensitivity)
            params["diarize_speaker_embedding"] = str(diarization_config.enable_speaker_embedding).lower()
        
        return params
    
    def _process_transcription_response(
        self,
        response: Dict[str, Any],
        start_time: float
    ) -> AudioTranscriptionResponse:
        """Process Deepgram response into our response format."""
        processing_time = time.time() - start_time
        
        # Extract basic information from JSON response
        result = response.get('results', {})
        channels = result.get('channels', [])
        
        if not channels:
            raise Exception("No channels found in Deepgram response")
        
        channel = channels[0]
        alternatives = channel.get('alternatives', [])
        
        if not alternatives:
            raise Exception("No alternatives found in Deepgram response")
        
        alternative = alternatives[0]
        transcript = alternative.get('transcript', '')
        confidence = alternative.get('confidence', 0.0)
        
        # Get duration from response metadata
        metadata = response.get('metadata', {})
        duration = metadata.get('duration', 0.0)
        
        # Debug: Log the response structure
        self.logger.info(f"Response type: {type(response)}")
        self.logger.info(f"Response keys: {list(response.keys())}")
        self.logger.info(f"Result keys: {list(result.keys())}")
        
        # Process speaker segments
        segments = []
        speaker_stats = {}
        
        # Try to get speaker information from words first (most accurate for diarization)
        words = alternative.get('words', [])
        self.logger.info(f"Found words: {len(words) if words else 0} words")
        
        # Log some sample words to debug speaker assignment
        if words:
            sample_words = words[:5]  # First 5 words
            self.logger.info(f"Sample words with speakers: {[(w.get('word', ''), w.get('speaker', 'None')) for w in sample_words]}")
        
        if words:
            # Process words to create speaker segments
            current_speaker = None
            current_segment_start = None
            current_segment_words = []
            current_speaker_confidence_sum = 0.0
            current_speaker_word_count = 0
            
            for word in words:
                word_speaker = word.get('speaker')
                word_confidence = word.get('confidence', 0.0)
                word_text = word.get('word', '')
                word_start = word.get('start', 0.0)
                word_end = word.get('end', 0.0)
                
                # If speaker changes, finalize current segment
                if current_speaker is not None and word_speaker != current_speaker:
                    if current_segment_words:
                        segment_text = ' '.join(current_segment_words)
                        avg_confidence = current_speaker_confidence_sum / current_speaker_word_count if current_speaker_word_count > 0 else 0.0
                        
                        segment = SpeakerSegment(
                            speaker=current_speaker,
                            start=current_segment_start,
                            end=word_start,  # End of previous word
                            text=segment_text,
                            confidence=avg_confidence
                        )
                        segments.append(segment)
                        
                        # Update speaker statistics
                        if current_speaker not in speaker_stats:
                            speaker_stats[current_speaker] = {
                                'total_time': 0.0,
                                'segment_count': 0,
                                'confidence_sum': 0.0
                            }
                        
                        speaker_stats[current_speaker]['total_time'] += (word_start - current_segment_start)
                        speaker_stats[current_speaker]['segment_count'] += 1
                        speaker_stats[current_speaker]['confidence_sum'] += avg_confidence
                
                # Start new segment if speaker changed or first word
                if word_speaker != current_speaker:
                    current_speaker = word_speaker
                    current_segment_start = word_start
                    current_segment_words = []
                    current_speaker_confidence_sum = 0.0
                    current_speaker_word_count = 0
                
                # Add word to current segment
                current_segment_words.append(word_text)
                current_speaker_confidence_sum += word_confidence
                current_speaker_word_count += 1
            
            # Don't forget the last segment
            if current_speaker is not None and current_segment_words:
                segment_text = ' '.join(current_segment_words)
                avg_confidence = current_speaker_confidence_sum / current_speaker_word_count if current_speaker_word_count > 0 else 0.0
                
                # Get the end time of the last word
                last_word_end = words[-1].get('end', 0.0) if words else 0.0
                
                segment = SpeakerSegment(
                    speaker=current_speaker,
                    start=current_segment_start,
                    end=last_word_end,
                    text=segment_text,
                    confidence=avg_confidence
                )
                segments.append(segment)
                
                # Update speaker statistics for the last segment
                if current_speaker not in speaker_stats:
                    speaker_stats[current_speaker] = {
                        'total_time': 0.0,
                        'segment_count': 0,
                        'confidence_sum': 0.0
                    }
                
                speaker_stats[current_speaker]['total_time'] += (last_word_end - current_segment_start)
                speaker_stats[current_speaker]['segment_count'] += 1
                speaker_stats[current_speaker]['confidence_sum'] += avg_confidence
        
        # Fallback: Try to access utterances from the response if no words were found
        if not segments:
            utterances = result.get('utterances', [])
            self.logger.info(f"Found utterances: {len(utterances) if utterances else 0}")
            
            # If we have utterances but no segments from words, use utterances
            if utterances:
                self.logger.info(f"Using utterances for speaker segments: {len(utterances)} utterances")
                for utterance in utterances:
                    speaker_id = utterance.get('speaker')
                    start_time = utterance.get('start', 0.0)
                    end_time = utterance.get('end', 0.0)
                    text = utterance.get('transcript', '')
                    utterance_confidence = utterance.get('confidence', 0.0)
                    
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
        if result.get('language'):
            language = result['language']
        elif metadata.get('language'):
            language = metadata['language']
        
        # Create conversation format transcript
        conversation_transcript = self._create_conversation_transcript(segments)
        
        return AudioTranscriptionResponse(
            transcript=conversation_transcript,
            segments=segments,
            speakers=speakers,
            duration=duration,
            language=language,
            confidence=confidence,
            processing_time=processing_time
        )
    
    def _create_conversation_transcript(self, segments: List[SpeakerSegment]) -> str:
        """Create a conversation format transcript from speaker segments."""
        if not segments:
            return ""
        
        conversation_lines = []
        for segment in segments:
            speaker_name = f"speaker_{segment.speaker}"
            # Clean up the text and format it properly
            text = segment.text.strip()
            if text:
                conversation_lines.append(f'{speaker_name}: "{text}"')
        
        return "\n".join(conversation_lines)
    
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