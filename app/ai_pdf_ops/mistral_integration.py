"""
Mistral API Integration

Handles communication with Mistral AI API for text processing,
analysis, and AI-powered PDF operations.
"""

import aiohttp
import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
from .config import ai_pdf_config

logger = logging.getLogger(__name__)


class MistralAPIError(Exception):
    """Custom exception for Mistral API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class MistralAPI:
    """Client for Mistral AI API integration."""
    
    BASE_URL = "https://api.mistral.ai/v1"
    
    def __init__(self):
        self.api_key = ai_pdf_config.mistral_api_key
        self.model = ai_pdf_config.mistral_model
        self.max_tokens = ai_pdf_config.mistral_max_tokens
        self.temperature = ai_pdf_config.mistral_temperature
        
        if not self.api_key:
            logger.warning("Mistral API key not configured - AI features will be disabled")
        
    @staticmethod
    async def call_mistral(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a call to Mistral API endpoint.
        
        Args:
            endpoint: API endpoint (e.g., 'chat/completions')
            payload: Request payload
            
        Returns:
            Response data from Mistral API
            
        Raises:
            MistralAPIError: If API call fails
        """
        if not ai_pdf_config.mistral_api_key:
            raise MistralAPIError("Mistral API key not configured")
            
        headers = {
            "Authorization": f"Bearer {ai_pdf_config.mistral_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "n8n-tools-api/0.1.0"
        }
        
        url = f"{MistralAPI.BASE_URL}/{endpoint}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=ai_pdf_config.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response_data = await response.json()
                    
                    if response.status >= 400:
                        error_message = response_data.get('error', {}).get('message', 'Unknown error')
                        raise MistralAPIError(
                            message=f"Mistral API error: {error_message}",
                            status_code=response.status,
                            response_data=response_data
                        )
                    
                    return response_data
                    
        except aiohttp.ClientError as e:
            raise MistralAPIError(f"Network error calling Mistral API: {str(e)}")
        except asyncio.TimeoutError:
            raise MistralAPIError(f"Mistral API call timed out after {ai_pdf_config.timeout_seconds} seconds")
        except json.JSONDecodeError as e:
            raise MistralAPIError(f"Invalid JSON response from Mistral API: {str(e)}")
    
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            model: Optional[str] = None,
                            max_tokens: Optional[int] = None,
                            temperature: Optional[float] = None,
                            **kwargs) -> Dict[str, Any]:
        """
        Create a chat completion using Mistral API.
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model to use (defaults to configured model)
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation
            **kwargs: Additional parameters for the API
            
        Returns:
            Chat completion response
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            **kwargs
        }
        
        try:
            response = await self.call_mistral("chat/completions", payload)
            return response
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise
    
    async def analyze_text(self, 
                          text: str, 
                          task: str = "analyze",
                          context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze text using Mistral AI.
        
        Args:
            text: Text to analyze
            task: Analysis task description
            context: Additional context for analysis
            
        Returns:
            Analysis results
        """
        system_message = f"""You are an AI assistant specialized in document analysis. 
        Your task is to {task}. Provide structured, accurate analysis."""
        
        if context:
            system_message += f"\n\nAdditional context: {context}"
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ]
        
        return await self.chat_completion(messages)
    
    async def extract_structured_data(self, 
                                    text: str, 
                                    schema: Dict[str, Any],
                                    instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured data from text using Mistral AI.
        
        Args:
            text: Source text
            schema: JSON schema for expected output structure
            instructions: Additional extraction instructions
            
        Returns:
            Structured data extraction results
        """
        schema_str = json.dumps(schema, indent=2)
        
        system_message = f"""You are an expert at extracting structured data from text.
        Extract information according to this JSON schema:
        
        {schema_str}
        
        Return only valid JSON that matches the schema."""
        
        if instructions:
            system_message += f"\n\nAdditional instructions: {instructions}"
        
        user_message = f"Extract structured data from this text:\n\n{text}"
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        return await self.chat_completion(messages)
    
    async def summarize_content(self, 
                              text: str, 
                              summary_type: str = "concise",
                              max_length: Optional[int] = None) -> Dict[str, Any]:
        """
        Summarize text content using Mistral AI.
        
        Args:
            text: Text to summarize
            summary_type: Type of summary ('concise', 'detailed', 'bullet_points')
            max_length: Maximum length of summary
            
        Returns:
            Summary results
        """
        length_instruction = f" in maximum {max_length} words" if max_length else ""
        
        system_message = f"""You are an expert at creating {summary_type} summaries.
        Create a {summary_type} summary{length_instruction}."""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Summarize this text:\n\n{text}"}
        ]
        
        return await self.chat_completion(messages)
    
    async def health_check(self) -> bool:
        """
        Check if Mistral API is accessible and properly configured.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            messages = [{"role": "user", "content": "Hello"}]
            await self.chat_completion(messages, max_tokens=10)
            return True
        except Exception as e:
            logger.error(f"Mistral API health check failed: {str(e)}")
            return False


# Global Mistral API instance
mistral_api = MistralAPI()
