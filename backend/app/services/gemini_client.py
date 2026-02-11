"""
Gemini AI client that mimics AsyncOpenAI interface.

This module provides a wrapper around Google's Gemini API that presents
the same interface as OpenAI's AsyncOpenAI client, allowing for easy
switching between providers without code changes.

Usage:
    Basic usage with the same interface as AsyncOpenAI:
    
    >>> from app.services.gemini_client import GeminiClient
    >>> 
    >>> # Initialize client
    >>> client = GeminiClient(api_key="your-gemini-api-key")
    >>> 
    >>> # Use exactly like AsyncOpenAI
    >>> response = await client.chat.completions.create(
    ...     model="gemini-1.5-flash",
    ...     messages=[
    ...         {"role": "system", "content": "You are a helpful assistant"},
    ...         {"role": "user", "content": "Write a hello world function"}
    ...     ],
    ...     temperature=0.2,
    ...     max_tokens=2000
    ... )
    >>> 
    >>> # Access response the same way
    >>> print(response.choices[0].message.content)
    >>> print(f"Tokens used: {response.usage.total_tokens}")

Configuration:
    To use this client in your application, set these environment variables:
    
    LLM_PROVIDER=gemini
    GEMINI_API_KEY=your-api-key-here
    
    Get your API key from: https://makersuite.google.com/app/apikey

API Compatibility:
    This client implements the following OpenAI interface:
    - client.chat.completions.create()
    - Response structure with .choices[0].message.content
    - Usage statistics with .usage.total_tokens
    
    Supported message roles:
    - system: Prepended to first user message
    - user: User input
    - assistant: AI responses (for conversation history)
"""

import aiohttp
from typing import List, Dict, Any, Optional


class GeminiClient:
    """Gemini client that mimics AsyncOpenAI interface.
    
    This client provides a drop-in replacement for AsyncOpenAI by implementing
    the same interface structure (client.chat.completions.create()). It handles
    message format conversion between OpenAI and Gemini formats automatically.
    
    Args:
        api_key (str): Google Gemini API key. Get one from 
            https://makersuite.google.com/app/apikey
    
    Attributes:
        api_key (str): The Gemini API key
        base_url (str): Gemini API base URL
        chat (ChatCompletions): Chat completions interface
        
    Example:
        Basic usage:
        
        >>> client = GeminiClient(api_key="your-api-key")
        >>> response = await client.chat.completions.create(
        ...     model="gemini-1.5-flash",
        ...     messages=[{"role": "user", "content": "Hello"}]
        ... )
        >>> print(response.choices[0].message.content)
        
        With system message and conversation history:
        
        >>> messages = [
        ...     {"role": "system", "content": "You are a Python expert"},
        ...     {"role": "user", "content": "Write a function"},
        ...     {"role": "assistant", "content": "def example(): pass"},
        ...     {"role": "user", "content": "Add error handling"}
        ... ]
        >>> response = await client.chat.completions.create(
        ...     model="gemini-1.5-flash",
        ...     messages=messages,
        ...     temperature=0.7
        ... )
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.chat = ChatCompletions(self)


class ChatCompletions:
    """Chat completions namespace that mimics OpenAI structure.
    
    This class provides the .chat property of the client to match
    OpenAI's client.chat.completions.create() interface.
    
    Args:
        client (GeminiClient): Parent Gemini client instance
        
    Attributes:
        client (GeminiClient): Reference to parent client
        completions (Completions): Completions interface
    """
    
    def __init__(self, client: GeminiClient):
        self.client = client
        self.completions = Completions(client)


class Completions:
    """Completions interface that mimics OpenAI's chat.completions.
    
    This class implements the .create() method that matches OpenAI's
    chat completions API signature and behavior.
    
    Args:
        client (GeminiClient): Parent Gemini client instance
        
    Attributes:
        client (GeminiClient): Reference to parent client
    """
    
    def __init__(self, client: GeminiClient):
        self.client = client
    
    async def create(
        self,
        model: str = "gemini-1.5-flash",
        messages: List[Dict[str, str]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs
    ):
        """Create a chat completion using Gemini API.
        
        This method mimics OpenAI's chat.completions.create() interface,
        allowing for seamless switching between providers.
        
        Args:
            model (str, optional): Gemini model name. Defaults to "gemini-1.5-flash".
                Available models: gemini-1.5-flash, gemini-1.5-pro
            messages (List[Dict[str, str]], optional): List of message dictionaries.
                Each message should have 'role' and 'content' keys.
                Supported roles: 'system', 'user', 'assistant'
            temperature (float, optional): Sampling temperature between 0.0 and 1.0.
                Lower values make output more focused and deterministic.
                Defaults to 0.2.
            max_tokens (int, optional): Maximum number of tokens to generate.
                Defaults to 2000.
            **kwargs: Additional arguments (accepted for OpenAI compatibility but ignored)
            
        Returns:
            Response: OpenAI-compatible response object with:
                - choices[0].message.content: Generated text
                - choices[0].message.role: Always "assistant"
                - choices[0].finish_reason: Always "stop"
                - usage.total_tokens: Total tokens used
                - usage.prompt_tokens: Always 0 (not provided by Gemini)
                - usage.completion_tokens: Same as total_tokens
            
        Raises:
            Exception: If API call fails with details:
                - "Gemini rate limit exceeded" (status 429)
                - "Gemini API key invalid or quota exceeded" (status 403)
                - "Gemini API error" (other status codes)
                - "Unexpected Gemini response format" (malformed response)
                
        Example:
            Simple completion:
            
            >>> response = await client.chat.completions.create(
            ...     messages=[{"role": "user", "content": "Say hello"}]
            ... )
            >>> print(response.choices[0].message.content)
            
            With custom parameters:
            
            >>> response = await client.chat.completions.create(
            ...     model="gemini-1.5-flash",
            ...     messages=[
            ...         {"role": "system", "content": "Be concise"},
            ...         {"role": "user", "content": "Explain Python"}
            ...     ],
            ...     temperature=0.7,
            ...     max_tokens=500
            ... )
            
            Error handling:
            
            >>> try:
            ...     response = await client.chat.completions.create(
            ...         messages=[{"role": "user", "content": "Hello"}]
            ...     )
            ... except Exception as e:
            ...     print(f"API error: {e}")
        """
        if messages is None:
            messages = []
        
        # Convert OpenAI messages to Gemini format
        gemini_messages = self._convert_messages(messages)
        
        # Build request
        url = f"{self.client.base_url}/models/{model}:generateContent"
        params = {"key": self.client.api_key}
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        # Make API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, json=payload) as response:
                if response.status == 429:
                    raise Exception("Gemini rate limit exceeded. Try again later.")
                elif response.status == 403:
                    raise Exception("Gemini API key invalid or quota exceeded")
                elif response.status != 200:
                    error = await response.text()
                    raise Exception(f"Gemini API error (status {response.status}): {error}")
                
                data = await response.json()
                
                # Convert to OpenAI format
                return self._convert_response(data)
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict]:
        """Convert OpenAI message format to Gemini format.
        
        Handles the conversion between OpenAI's message structure and Gemini's
        contents structure. System messages are prepended to the first user
        message since Gemini doesn't have a separate system role.
        
        Args:
            messages (List[Dict[str, str]]): OpenAI format messages
        
        Returns:
            List[Dict]: Gemini format contents
            
        OpenAI format:
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
            
        Gemini format:
            [
                {"parts": [{"text": "You are helpful\n\nHello"}]},
                {"parts": [{"text": "Hi there!"}]}
            ]
            
        Note:
            - System messages are prepended to the first user message
            - Only the first system message is used
            - Assistant messages maintain conversation history
        """
        gemini_contents = []
        system_message = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                text = msg["content"]
                if system_message:
                    text = f"{system_message}\n\n{text}"
                    system_message = ""  # Only prepend once
                gemini_contents.append({
                    "parts": [{"text": text}]
                })
            elif msg["role"] == "assistant":
                gemini_contents.append({
                    "parts": [{"text": msg["content"]}]
                })
        
        return gemini_contents
    
    def _convert_response(self, gemini_response: Dict) -> Any:
        """Convert Gemini response to OpenAI format.
        
        Transforms Gemini's response structure into an OpenAI-compatible
        response object that can be accessed the same way.
        
        Args:
            gemini_response (Dict): Raw Gemini API response
            
        Returns:
            Response: OpenAI-compatible response object
            
        Raises:
            Exception: If response format is unexpected or malformed
            
        Gemini format:
            {
                "candidates": [{
                    "content": {
                        "parts": [{"text": "Generated response"}]
                    }
                }],
                "usageMetadata": {
                    "totalTokenCount": 42
                }
            }
            
        OpenAI format (returned):
            Response object with:
                .choices[0].message.content = "Generated response"
                .choices[0].message.role = "assistant"
                .choices[0].finish_reason = "stop"
                .usage.total_tokens = 42
                .usage.prompt_tokens = 0
                .usage.completion_tokens = 42
        """
        
        class Choice:
            """Mimics OpenAI Choice object."""
            def __init__(self, content: str):
                self.message = type('Message', (object,), {
                    'content': content,
                    'role': 'assistant'
                })()
                self.finish_reason = 'stop'
        
        class Usage:
            """Mimics OpenAI Usage object."""
            def __init__(self, tokens: int):
                self.total_tokens = tokens
                self.prompt_tokens = 0
                self.completion_tokens = tokens
        
        class Response:
            """Mimics OpenAI Response object."""
            def __init__(self, content: str, tokens: int):
                self.choices = [Choice(content)]
                self.usage = Usage(tokens)
        
        # Extract content from Gemini response
        try:
            content = gemini_response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected Gemini response format: {e}")
        
        tokens = gemini_response.get("usageMetadata", {}).get("totalTokenCount", 0)
        
        return Response(content, tokens)
