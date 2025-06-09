"""
Embeddings Processor

Implements text embeddings generation for PDF content using sentence transformers
and semantic search capabilities for document analysis.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import asyncio
import hashlib
import json

from .base import EmbeddingsOperation, AIOperationResult
from .config import ai_pdf_config
from .mistral_integration import mistral_api, MistralAPIError

logger = logging.getLogger(__name__)


class EmbeddingsProcessor(EmbeddingsOperation):
    """Embeddings processor for generating and searching text embeddings from PDF content."""
    
    def __init__(self):
        super().__init__()
        self.embeddings_enabled = ai_pdf_config.embeddings_enabled
        self.embeddings_model = ai_pdf_config.embeddings_model
        self.chunk_size = ai_pdf_config.embeddings_chunk_size
        self.overlap = ai_pdf_config.embeddings_overlap
        self.cache_enabled = ai_pdf_config.cache_enabled
        self._embedding_cache = {}  # Simple in-memory cache
    
    async def process(self, pdf_content: bytes, **kwargs) -> AIOperationResult:
        """
        Main processing method for embeddings operations.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            **kwargs: Additional parameters (operation_type, query, etc.)
            
        Returns:
            AIOperationResult with embeddings results
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not await self.validate_input(pdf_content):
                return self._create_result(
                    success=False,
                    errors=["Invalid PDF content provided"],
                    processing_time=time.time() - start_time
                )
            
            if not self.embeddings_enabled:
                return self._create_result(
                    success=False,
                    errors=["Embeddings functionality is disabled"],
                    processing_time=time.time() - start_time
                )
            
            # Extract parameters
            operation_type = kwargs.get('operation_type', 'generate')
            chunk_size = kwargs.get('chunk_size', self.chunk_size)
            
            # Perform embeddings operation based on type
            if operation_type == 'generate':
                result = await self.generate_text_embeddings(pdf_content, chunk_size)
            elif operation_type == 'search':
                query = kwargs.get('query', '')
                top_k = kwargs.get('top_k', 5)
                result = await self.similarity_search(pdf_content, query, top_k)
            else:
                # Default to generate
                result = await self.generate_text_embeddings(pdf_content, chunk_size)
            
            result.processing_time_seconds = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"Embeddings processing error: {str(e)}")
            return self._create_result(
                success=False,
                errors=[f"Embeddings processing failed: {str(e)}"],
                processing_time=time.time() - start_time
            )
    
    async def generate_text_embeddings(self, pdf_content: bytes, chunk_size: Optional[int] = None) -> AIOperationResult:
        """
        Generate embeddings for text content in PDF.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            chunk_size: Size of text chunks for embeddings
            
        Returns:
            AIOperationResult with embeddings data
        """
        start_time = time.time()
        
        try:
            # First extract text from PDF (placeholder implementation)
            extracted_text = await self._extract_text_from_pdf(pdf_content)
            
            if not extracted_text.strip():
                return self._create_result(
                    success=False,
                    errors=["No text content found in PDF"],
                    processing_time=time.time() - start_time
                )
            
            # Split text into chunks
            chunks = self._split_text_into_chunks(extracted_text, chunk_size or self.chunk_size)
            
            # Generate embeddings for each chunk
            embeddings_data = await self._generate_embeddings_for_chunks(chunks)
            
            # Use Mistral AI for content analysis and enhancement
            content_analysis = await self._analyze_content_with_ai(extracted_text, chunks)
            
            metadata = {
                "embeddings_model": self.embeddings_model,
                "chunk_size": chunk_size or self.chunk_size,
                "overlap": self.overlap,
                "total_chunks": len(chunks),
                "total_text_length": len(extracted_text),
                "embedding_dimensions": 384  # Typical for all-MiniLM-L6-v2
            }
            
            return self._create_result(
                success=True,
                data={
                    "embeddings": embeddings_data,
                    "chunks": chunks,
                    "text_content": extracted_text,
                    "content_analysis": content_analysis
                },
                metadata=metadata,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Embeddings generation error: {str(e)}")
            return self._create_result(
                success=False,
                errors=[f"Embeddings generation failed: {str(e)}"],
                processing_time=time.time() - start_time
            )
    
    async def similarity_search(self, pdf_content: bytes, query: str, top_k: int = 5) -> AIOperationResult:
        """
        Perform similarity search against PDF content.
        
        Args:
            pdf_content: Raw PDF file content as bytes
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            AIOperationResult with similarity search results
        """
        start_time = time.time()
        
        try:
            if not query.strip():
                return self._create_result(
                    success=False,
                    errors=["Search query cannot be empty"],
                    processing_time=time.time() - start_time
                )
            
            # First generate embeddings for the document
            embeddings_result = await self.generate_text_embeddings(pdf_content)
            
            if not embeddings_result.success:
                return embeddings_result
            
            chunks = embeddings_result.data["chunks"]
            embeddings = embeddings_result.data["embeddings"]
            
            # Generate embedding for query
            query_embedding = await self._generate_single_embedding(query)
            
            # Calculate similarities and find top matches
            similarity_results = await self._calculate_similarities(
                query_embedding, embeddings, chunks, top_k
            )
            
            # Use Mistral AI to enhance search results with context
            enhanced_results = await self._enhance_search_results_with_ai(
                query, similarity_results
            )
            
            metadata = {
                "query": query,
                "top_k": top_k,
                "total_chunks_searched": len(chunks),
                "embeddings_model": self.embeddings_model,
                "search_type": "semantic_similarity"
            }
            
            return self._create_result(
                success=True,
                data={
                    "search_results": enhanced_results,
                    "raw_similarities": similarity_results,
                    "query": query
                },
                metadata=metadata,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Similarity search error: {str(e)}")
            return self._create_result(
                success=False,
                errors=[f"Similarity search failed: {str(e)}"],
                processing_time=time.time() - start_time
            )
    
    async def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF content.
        
        This is a placeholder - in a real implementation, you would:
        1. Use pypdf or similar library to extract text
        2. Or integrate with the OCR module for scanned PDFs
        """
        # Simulate text extraction delay
        await asyncio.sleep(0.1)
        
        # Placeholder text extraction
        placeholder_text = f"""
        This is placeholder text extracted from a PDF document for embeddings processing.
        
        The document contains various sections including:
        - Introduction and overview
        - Technical specifications and requirements
        - Implementation details and methodology
        - Data analysis and results
        - Conclusions and recommendations
        
        In a real implementation, this would contain the actual text content
        extracted from the PDF using libraries like pypdf, pdfplumber, or
        integrated with the OCR module for scanned documents.
        
        The text would be properly formatted and cleaned for optimal
        embeddings generation and semantic search capabilities.
        
        Key topics covered in this document:
        - Machine learning and artificial intelligence
        - Natural language processing techniques
        - Document analysis and information extraction
        - Workflow automation and integration
        - API design and microservices architecture
        
        This placeholder demonstrates the structure and format of text
        that would be processed for embeddings generation.
        """
        
        return placeholder_text.strip()
    
    def _split_text_into_chunks(self, text: str, chunk_size: int) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks for embeddings generation.
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - self.overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            if chunk_text.strip():
                chunks.append({
                    "id": len(chunks),
                    "text": chunk_text,
                    "start_word": i,
                    "end_word": min(i + chunk_size, len(words)),
                    "word_count": len(chunk_words)
                })
            
            # Break if we've reached the end
            if i + chunk_size >= len(words):
                break
        
        return chunks
    
    async def _generate_embeddings_for_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for text chunks.
        
        This is a placeholder implementation. In reality, you would use:
        - sentence-transformers library
        - OpenAI embeddings API
        - Local embedding models
        """
        embeddings_data = []
        
        for chunk in chunks:
            # Simulate embedding generation delay
            await asyncio.sleep(0.05)
            
            # Check cache first
            cache_key = self._get_cache_key(chunk["text"])
            if self.cache_enabled and cache_key in self._embedding_cache:
                embedding_vector = self._embedding_cache[cache_key]
            else:
                # Generate placeholder embedding (normally would be actual embedding)
                embedding_vector = await self._generate_single_embedding(chunk["text"])
                
                # Cache the result
                if self.cache_enabled:
                    self._embedding_cache[cache_key] = embedding_vector
            
            embeddings_data.append({
                "chunk_id": chunk["id"],
                "embedding": embedding_vector,
                "text_preview": chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"],
                "word_count": chunk["word_count"]
            })
        
        return embeddings_data
    
    async def _generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate a single embedding vector for text.
        
        This is a placeholder that returns a random vector.
        In reality, you would use actual embedding models.
        """
        # Simulate embedding generation
        await asyncio.sleep(0.02)
        
        # Return placeholder embedding (384 dimensions for all-MiniLM-L6-v2)
        import random
        random.seed(hash(text) % (2**32))  # Deterministic based on text
        return [random.uniform(-1, 1) for _ in range(384)]
    
    async def _calculate_similarities(self, 
                                   query_embedding: List[float], 
                                   embeddings: List[Dict[str, Any]], 
                                   chunks: List[Dict[str, Any]], 
                                   top_k: int) -> List[Dict[str, Any]]:
        """
        Calculate cosine similarities and return top matches.
        """
        similarities = []
        
        for i, embedding_data in enumerate(embeddings):
            # Calculate cosine similarity (placeholder implementation)
            similarity_score = self._cosine_similarity(query_embedding, embedding_data["embedding"])
            
            similarities.append({
                "chunk_id": embedding_data["chunk_id"],
                "similarity_score": similarity_score,
                "text": chunks[i]["text"],
                "word_count": chunks[i]["word_count"]
            })
        
        # Sort by similarity score and return top k
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        """
        import math
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def _analyze_content_with_ai(self, full_text: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use Mistral AI to analyze content and provide insights.
        """
        try:
            # Analyze the overall content
            analysis_result = await mistral_api.analyze_text(
                text=full_text[:2000],  # Limit text length for API
                task="analyze the content and identify key themes, topics, and important information",
                context="This is text extracted from a PDF document for embeddings and search"
            )
            
            if analysis_result and 'choices' in analysis_result:
                analysis = analysis_result['choices'][0]['message']['content']
                return {
                    "content_analysis": analysis,
                    "chunk_summary": {
                        "total_chunks": len(chunks),
                        "avg_chunk_length": sum(c["word_count"] for c in chunks) / len(chunks) if chunks else 0,
                        "content_coverage": "complete"
                    },
                    "key_insights": self._extract_key_insights(chunks)
                }
            else:
                return {"content_analysis": "Content processed but AI analysis unavailable"}
                
        except Exception as e:
            logger.warning(f"AI content analysis failed: {str(e)}")
            return {"content_analysis": "Content processed but AI analysis failed"}
    
    async def _enhance_search_results_with_ai(self, query: str, similarity_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use Mistral AI to enhance search results with context and explanations.
        """
        try:
            enhanced_results = []
            
            for result in similarity_results:
                # Create context for AI analysis
                context_text = f"Query: {query}\nMatched text: {result['text'][:500]}"
                
                explanation_result = await mistral_api.analyze_text(
                    text=context_text,
                    task="explain why this text matches the query and provide context",
                    context="This is a search result from semantic similarity matching"
                )
                
                explanation = "Semantic match based on embedding similarity"
                if explanation_result and 'choices' in explanation_result:
                    explanation = explanation_result['choices'][0]['message']['content']
                
                enhanced_result = {
                    **result,
                    "explanation": explanation,
                    "relevance_category": self._categorize_relevance(result["similarity_score"]),
                    "key_phrases": self._extract_key_phrases(result["text"])
                }
                
                enhanced_results.append(enhanced_result)
            
            return enhanced_results
            
        except Exception as e:
            return similarity_results
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _extract_key_insights(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Extract key insights from text chunks."""
        insights = []
        
        total_words = sum(chunk["word_count"] for chunk in chunks)
        avg_chunk_size = total_words / len(chunks) if chunks else 0
        
        insights.append(f"Document contains {len(chunks)} text chunks with average {avg_chunk_size:.0f} words per chunk")
        
        if total_words > 5000:
            insights.append("Large document - comprehensive embeddings coverage achieved")
        elif total_words < 500:
            insights.append("Short document - may benefit from smaller chunk sizes")
        
        return insights
    
    def _categorize_relevance(self, similarity_score: float) -> str:
        """Categorize relevance based on similarity score."""
        if similarity_score > 0.8:
            return "highly_relevant"
        elif similarity_score > 0.6:
            return "relevant"
        elif similarity_score > 0.4:
            return "somewhat_relevant"
        else:
            return "low_relevance"
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text (simple implementation)."""
        # Simple keyword extraction based on word frequency
        words = text.lower().split()
        
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top keywords
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [word for word, freq in top_words]
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _extract_key_insights(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Extract key insights from text chunks."""
        insights = []
        
        total_words = sum(chunk["word_count"] for chunk in chunks)
        avg_chunk_size = total_words / len(chunks) if chunks else 0
        
        insights.append(f"Document contains {len(chunks)} text chunks with average {avg_chunk_size:.0f} words per chunk")
        
        if total_words > 5000:
            insights.append("Large document - comprehensive embeddings coverage achieved")
        elif total_words < 500:
            insights.append("Short document - may benefit from smaller chunk sizes")
        
        return insights
    
    def _categorize_relevance(self, similarity_score: float) -> str:
        """Categorize relevance based on similarity score."""
        if similarity_score > 0.8:
            return "highly_relevant"
        elif similarity_score > 0.6:
            return "relevant"
        elif similarity_score > 0.4:
            return "somewhat_relevant"
        else:
            return "low_relevance"
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text (simple implementation)."""
        # Simple keyword extraction based on word frequency
        words = text.lower().split()
        
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top keywords
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [word for word, freq in top_words]
