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
    
    async def analyze_audio_comparison(
        self, 
        transcript1: str, 
        transcript2: str, 
        witness1_name: str = "Witness 1", 
        witness2_name: str = "Witness 2"
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Analyze two audio transcripts and generate comparison analysis.
        
        Returns:
            tuple: (witnesses_analysis, detailed_analysis)
        """
        try:
            prompt = f"""
            You are a legal analyst comparing two witness statements. Analyze the following transcripts and provide a comprehensive comparison.

            WITNESS 1 ({witness1_name}):
            {transcript1}

            WITNESS 2 ({witness2_name}):
            {transcript2}

            IMPORTANT: You must respond with ONLY valid JSON. No additional text, explanations, or formatting.

            Required JSON structure:
            {{
                "witnesses": [
                    {{
                        "id": "ac1",
                        "witnessName": "{witness1_name}",
                        "witnessImage": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face",
                        "audioId": "media1",
                        "summary": "Brief summary of what this witness said",
                        "transcript": "Key excerpt from transcript",
                        "contradictions": ["List of contradictions with other evidence"],
                        "similarities": ["List of similarities with other witness"],
                        "grayAreas": ["List of unclear or ambiguous statements"]
                    }},
                    {{
                        "id": "ac2",
                        "witnessName": "{witness2_name}",
                        "witnessImage": "https://images.unsplash.com/photo-1494790108755-2616b2abff16?w=150&h=150&fit=crop&crop=face",
                        "audioId": "media2",
                        "summary": "Brief summary of what this witness said",
                        "transcript": "Key excerpt from transcript",
                        "contradictions": ["List of contradictions with other evidence"],
                        "similarities": ["List of similarities with other witness"],
                        "grayAreas": ["List of unclear or ambiguous statements"]
                    }}
                ],
                "detailedAnalysis": [
                    {{
                        "topic": "Topic being compared",
                        "witness1": "What witness 1 said about this topic",
                        "witness2": "What witness 2 said about this topic",
                        "status": "contradiction",
                        "details": "Detailed explanation of the comparison"
                    }},
                    {{
                        "topic": "Another topic",
                        "witness1": "What witness 1 said",
                        "witness2": "What witness 2 said",
                        "status": "similarity",
                        "details": "Explanation"
                    }}
                ]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert legal analyst specializing in witness statement comparison and contradiction analysis. Provide detailed, accurate analysis of witness statements."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"OpenAI response content: {content[:200]}...")
            
            if not content:
                logger.error("OpenAI returned empty content")
                raise ValueError("Empty response from OpenAI")
            
            # Clean up markdown formatting if present
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]   # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```
            
            content = content.strip()
            logger.info(f"Cleaned content: {content[:200]}...")
            
            # Try to parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {json_err}")
                logger.error(f"Raw content: {content}")
                raise ValueError(f"Invalid JSON response from OpenAI: {json_err}")
            
            witnesses = result.get("witnesses", [])
            detailed_analysis = result.get("detailedAnalysis", [])
            
            if not witnesses or not detailed_analysis:
                logger.error("OpenAI response missing required fields")
                logger.error(f"Witnesses: {witnesses}, Analysis: {detailed_analysis}")
                raise ValueError("Incomplete response from OpenAI")
            
            return witnesses, detailed_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze audio comparison: {str(e)}")
            
            # Try with a simpler prompt as fallback
            try:
                logger.info("Attempting fallback analysis with simpler prompt...")
                simple_prompt = f"""
                Compare these two witness statements and return JSON only:
                
                Statement 1: {transcript1[:500]}...
                Statement 2: {transcript2[:500]}...
                
                Return this exact JSON structure:
                {{"witnesses":[{{"id":"ac1","witnessName":"{witness1_name}","witnessImage":"https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face","audioId":"media1","summary":"Brief summary","transcript":"Key excerpt","contradictions":["Contradiction 1"],"similarities":["Similarity 1"],"grayAreas":["Gray area 1"]}},{{"id":"ac2","witnessName":"{witness2_name}","witnessImage":"https://images.unsplash.com/photo-1494790108755-2616b2abff16?w=150&h=150&fit=crop&crop=face","audioId":"media2","summary":"Brief summary","transcript":"Key excerpt","contradictions":["Contradiction 1"],"similarities":["Similarity 1"],"grayAreas":["Gray area 1"]}}],"detailedAnalysis":[{{"topic":"Topic 1","witness1":"Statement 1","witness2":"Statement 2","status":"similarity","details":"Explanation"}}]}}
                """
                
                fallback_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a legal analyst. Return only valid JSON."},
                        {"role": "user", "content": simple_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                fallback_content = fallback_response.choices[0].message.content.strip()
                if fallback_content:
                    fallback_result = json.loads(fallback_content)
                    witnesses = fallback_result.get("witnesses", [])
                    detailed_analysis = fallback_result.get("detailedAnalysis", [])
                    if witnesses and detailed_analysis:
                        logger.info("Fallback analysis successful")
                        return witnesses, detailed_analysis
                        
            except Exception as fallback_error:
                logger.error(f"Fallback analysis also failed: {fallback_error}")
            
            # Return default structure on error
            default_witnesses = [
                {
                    "id": "ac1",
                    "witnessName": witness1_name,
                    "witnessImage": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face",
                    "audioId": "media1",
                    "summary": "Analysis failed - manual review required",
                    "transcript": transcript1[:200] + "..." if len(transcript1) > 200 else transcript1,
                    "contradictions": ["Analysis unavailable"],
                    "similarities": ["Analysis unavailable"],
                    "grayAreas": ["Analysis unavailable"]
                },
                {
                    "id": "ac2",
                    "witnessName": witness2_name,
                    "witnessImage": "https://images.unsplash.com/photo-1494790108755-2616b2abff16?w=150&h=150&fit=crop&crop=face",
                    "audioId": "media2",
                    "summary": "Analysis failed - manual review required",
                    "transcript": transcript2[:200] + "..." if len(transcript2) > 200 else transcript2,
                    "contradictions": ["Analysis unavailable"],
                    "similarities": ["Analysis unavailable"],
                    "grayAreas": ["Analysis unavailable"]
                }
            ]
            
            default_analysis = [
                {
                    "topic": "Analysis Error",
                    "witness1": "Unable to analyze",
                    "witness2": "Unable to analyze",
                    "status": "gray_area",
                    "details": "AI analysis failed - manual review required"
                }
            ]
            
            return default_witnesses, default_analysis


    async def query_knowledge_base(self, query: str, case_id: str) -> str:
        """
        Query the knowledge base for a given query.
        """
        print(f"Querying knowledge base for query: knowledge_base_query: {query} case_id: {case_id}")
        prompt = f"You are a helpful AI assistant that answers questions based on the provided document context. Use the context below to answer the user's question. If the answer cannot be found in the context, say so clearly. Context: {context}"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
        )
        return response.choices[0].message.content
