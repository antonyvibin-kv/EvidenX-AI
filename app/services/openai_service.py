import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for OpenAI API integration for transcript analysis."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"  # Using GPT-4o for better analysis capabilities
    
    async def analyze_transcripts(
        self, 
        transcripts: List[str], 
        case_id: str
    ) -> Dict[str, Any]:
        """
        Analyze multiple transcripts to identify similarities, contradictions, 
        gray areas, and suggest follow-up questions.
        
        Args:
            transcripts: List of transcript texts to analyze
            case_id: Case identifier for context
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Prepare the transcripts for analysis
            transcript_text = self._prepare_transcripts_for_analysis(transcripts)
            
            # Create the analysis prompt
            prompt = self._create_analysis_prompt(transcript_text, case_id)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert legal analyst specializing in transcript analysis. Your task is to analyze multiple transcripts from the same case and identify patterns, contradictions, and areas that need clarification."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=4000
            )
            
            # Parse the response
            analysis_result = self._parse_analysis_response(response.choices[0].message.content)
            
            logger.info(f"Successfully analyzed {len(transcripts)} transcripts for case {case_id}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed to analyze transcripts for case {case_id}: {str(e)}")
            raise Exception(f"OpenAI analysis failed: {str(e)}")
    
    def _prepare_transcripts_for_analysis(self, transcripts: List[str]) -> str:
        """Prepare transcripts for analysis by formatting them."""
        formatted_transcripts = []
        
        for i, transcript in enumerate(transcripts, 1):
            formatted_transcripts.append(f"TRANSCRIPT {i}:\n{transcript}\n")
        
        return "\n".join(formatted_transcripts)
    
    def _create_analysis_prompt(self, transcript_text: str, case_id: str) -> str:
        """Create the analysis prompt for OpenAI."""
        return f"""
Please analyze the following transcripts from case {case_id} and provide a structured comparison analysis.

TRANSCRIPTS:
{transcript_text}

Analyze these transcripts and identify key topics where witnesses provide information. For each topic, compare the statements and determine if they show:
- "similarity" - when statements are consistent or corroborating
- "contradiction" - when statements conflict or contradict each other  
- "gray_area" - when information is unclear, ambiguous, or incomplete

Return your analysis as a JSON object with this exact format:
{{
    "comparisons": [
        {{
            "topic": "Topic name (e.g., 'Time of incident', 'Suspect description')",
            "witness1": "Statement from first witness/transcript",
            "witness2": "Statement from second witness/transcript", 
            "status": "similarity|contradiction|gray_area",
            "details": "Brief explanation of the comparison result"
        }}
    ],
    "followUpQuestions": [
        "Specific question that can be asked to both witnesses",
        "Another follow-up question",
        "Third follow-up question"
    ]
}}

Focus on factual comparisons and be specific with quotes. Include 8-12 comparison points covering the most important aspects of the case. Generate 5-8 follow-up questions that would help clarify contradictions and gray areas.
"""
    
    def _parse_analysis_response(self, response_content: str) -> Dict[str, Any]:
        """Parse the OpenAI response and ensure it's valid JSON."""
        try:
            # Try to extract JSON object from the response
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = response_content[start_idx:end_idx]
            analysis_result = json.loads(json_str)
            
            # Validate that it's a dict and has required fields
            if not isinstance(analysis_result, dict):
                raise ValueError("Response is not a dictionary")
            
            # Ensure required fields exist
            if "comparisons" not in analysis_result:
                analysis_result["comparisons"] = []
            if "followUpQuestions" not in analysis_result:
                analysis_result["followUpQuestions"] = []
            
            # Validate each comparison item
            for item in analysis_result.get("comparisons", []):
                required_fields = ["topic", "witness1", "witness2", "status", "details"]
                for field in required_fields:
                    if field not in item:
                        raise ValueError(f"Missing required field: {field}")
                
                # Validate status field
                if item["status"] not in ["similarity", "contradiction", "gray_area"]:
                    item["status"] = "gray_area"  # Default to gray_area for invalid status
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
            # Return a fallback structure
            return {
                "comparisons": [{
                    "topic": "Analysis Error",
                    "witness1": "Unable to parse response",
                    "witness2": "Please try again",
                    "status": "gray_area",
                    "details": "Failed to parse OpenAI response"
                }],
                "followUpQuestions": ["Unable to generate questions due to parsing error"]
            }
        except Exception as e:
            logger.error(f"Failed to parse analysis response: {str(e)}")
            return {
                "comparisons": [{
                    "topic": "Analysis Error", 
                    "witness1": "Error occurred",
                    "witness2": "Please try again",
                    "status": "gray_area",
                    "details": f"Error: {str(e)}"
                }],
                "followUpQuestions": ["Unable to generate questions due to error"]
            }
    
    async def generate_follow_up_questions(
        self, 
        transcript: str, 
        case_id: str
    ) -> List[str]:
        """
        Generate additional follow-up questions based on the transcript.
        
        Args:
            transcript: The transcribed text
            case_id: Case identifier
            
        Returns:
            List of additional follow-up questions
        """
        try:
            prompt = f"""
Based on the following audio transcript from case {case_id}, generate 5 specific follow-up questions that would help clarify the situation and gather more information.

TRANSCRIPT:
{transcript}

Please provide 5 specific, actionable follow-up questions that would help resolve any ambiguities or gather additional details. Format as a JSON array of strings.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert legal investigator. Generate specific, actionable follow-up questions based on transcript analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=1000
            )
            
            # Parse the response
            content = response.choices[0].message.content
            try:
                questions = json.loads(content)
                if isinstance(questions, list):
                    return questions
                else:
                    return [str(questions)]
            except json.JSONDecodeError:
                # If JSON parsing fails, split by lines and clean up
                lines = content.split('\n')
                questions = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('[') and not line.startswith(']'):
                        # Remove numbering and quotes
                        line = line.lstrip('0123456789.- ').strip('"\'')
                        if line:
                            questions.append(line)
                return questions[:5]  # Return max 5 questions
                
        except Exception as e:
            logger.error(f"Failed to generate follow-up questions for case {case_id}: {str(e)}")
            return ["Unable to generate additional questions due to an error"]

    async def generate_audio_title_and_summary(self, transcript: str, case_id: str) -> tuple[str, str]:
        """
        Generate a title and summary for audio transcript using OpenAI.
        
        Args:
            transcript: The transcribed text from the audio
            case_id: The case ID for context
            
        Returns:
            tuple: (title, summary)
        """
        try:
            prompt = f"""
            Based on the following audio transcript from a legal case investigation, generate:
            1. A concise, descriptive title (max 50 characters)
            2. A brief summary (max 200 characters)
            
            Transcript: {transcript}
            
            Please respond in the following JSON format:
            {{
                "title": "Brief descriptive title",
                "summary": "Brief summary of the content"
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that helps generate titles and summaries for legal investigation audio transcripts. Be concise and professional."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"Generated title and summary for case {case_id}")
            
            # Parse JSON response
            try:
                import json
                result = json.loads(content)
                title = result.get("title", "Audio Recording")
                summary = result.get("summary", "Audio recording from investigation")
                return title, summary
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                lines = content.split('\n')
                title = "Audio Recording"
                summary = "Audio recording from investigation"
                
                for line in lines:
                    line = line.strip()
                    if 'title' in line.lower():
                        title = line.split(':', 1)[-1].strip().strip('"\'')
                    elif 'summary' in line.lower():
                        summary = line.split(':', 1)[-1].strip().strip('"\'')
                
                return title, summary
                
        except Exception as e:
            logger.error(f"Failed to generate title and summary for case {case_id}: {str(e)}")
            return "Audio Recording", "Audio recording from investigation"