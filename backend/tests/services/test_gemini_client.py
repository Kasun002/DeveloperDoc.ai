"""
Unit tests for Gemini Client.

Tests the Gemini client wrapper that mimics AsyncOpenAI interface,
including message format conversion, response format conversion,
and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientSession, ClientResponse
from app.services.gemini_client import GeminiClient, ChatCompletions, Completions


def create_mock_response(status=200, json_data=None, text_data=None):
    """Helper function to create a properly mocked aiohttp response."""
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = status
    if json_data is not None:
        mock_response.json = AsyncMock(return_value=json_data)
    if text_data is not None:
        mock_response.text = AsyncMock(return_value=text_data)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    return mock_response


def create_mock_session(mock_response):
    """Helper function to create a properly mocked aiohttp session."""
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    return mock_session


@pytest.mark.asyncio
class TestGeminiClient:
    """Test suite for GeminiClient."""
    
    def test_client_initialization(self):
        """Test that GeminiClient initializes correctly."""
        client = GeminiClient(api_key="test-api-key")
        
        assert client.api_key == "test-api-key"
        assert client.base_url == "https://generativelanguage.googleapis.com/v1beta"
        assert isinstance(client.chat, ChatCompletions)
        assert isinstance(client.chat.completions, Completions)
    
    async def test_create_with_simple_message(self):
        """Test that create() handles a simple user message."""
        client = GeminiClient(api_key="test-key")
        
        # Mock Gemini API response
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Hello! How can I help you?"}]
                }
            }],
            "usageMetadata": {
                "totalTokenCount": 25
            }
        }
        
        mock_response = create_mock_response(status=200, json_data=mock_response_data)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = await client.chat.completions.create(
                model="gemini-2.0-flash",
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            assert response.choices[0].message.content == "Hello! How can I help you?"
            assert response.choices[0].message.role == "assistant"
            assert response.choices[0].finish_reason == "stop"
            assert response.usage.total_tokens == 25
    
    async def test_create_with_system_and_user_messages(self):
        """Test that create() properly handles system and user messages."""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "I am a helpful assistant."}]
                }
            }],
            "usageMetadata": {
                "totalTokenCount": 15
            }
        }
        
        mock_response = create_mock_response(status=200, json_data=mock_response_data)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = await client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "Who are you?"}
                ]
            )
            
            # Verify the request was made with system message prepended
            call_args = mock_session.post.call_args
            payload = call_args.kwargs['json']
            
            # System message should be prepended to first user message
            assert len(payload['contents']) == 1
            assert "You are a helpful assistant" in payload['contents'][0]['parts'][0]['text']
            assert "Who are you?" in payload['contents'][0]['parts'][0]['text']
    
    async def test_create_with_conversation_history(self):
        """Test that create() handles multi-turn conversations."""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "The capital of France is Paris."}]
                }
            }],
            "usageMetadata": {
                "totalTokenCount": 30
            }
        }
        
        mock_response = create_mock_response(status=200, json_data=mock_response_data)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = await client.chat.completions.create(
                messages=[
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "What is the capital of France?"}
                ]
            )
            
            # Verify the request includes all messages
            call_args = mock_session.post.call_args
            payload = call_args.kwargs['json']
            
            assert len(payload['contents']) == 3
            assert payload['contents'][0]['parts'][0]['text'] == "Hello"
            assert payload['contents'][1]['parts'][0]['text'] == "Hi there!"
            assert payload['contents'][2]['parts'][0]['text'] == "What is the capital of France?"
    
    async def test_create_with_custom_parameters(self):
        """Test that create() respects custom temperature and max_tokens."""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Response"}]
                }
            }],
            "usageMetadata": {
                "totalTokenCount": 10
            }
        }
        
        mock_response = create_mock_response(status=200, json_data=mock_response_data)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            await client.chat.completions.create(
                messages=[{"role": "user", "content": "Test"}],
                temperature=0.8,
                max_tokens=1000
            )
            
            # Verify the request includes custom parameters
            call_args = mock_session.post.call_args
            payload = call_args.kwargs['json']
            
            assert payload['generationConfig']['temperature'] == 0.8
            assert payload['generationConfig']['maxOutputTokens'] == 1000
    
    async def test_create_handles_rate_limit_error(self):
        """Test that create() raises appropriate error for rate limit (429)."""
        client = GeminiClient(api_key="test-key")
        
        mock_response = create_mock_response(status=429)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(Exception, match="Gemini rate limit exceeded"):
                await client.chat.completions.create(
                    messages=[{"role": "user", "content": "Test"}]
                )
    
    async def test_create_handles_invalid_api_key_error(self):
        """Test that create() raises appropriate error for invalid API key (403)."""
        client = GeminiClient(api_key="invalid-key")
        
        mock_response = create_mock_response(status=403)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(Exception, match="Gemini API key invalid or quota exceeded"):
                await client.chat.completions.create(
                    messages=[{"role": "user", "content": "Test"}]
                )
    
    async def test_create_handles_generic_api_error(self):
        """Test that create() raises appropriate error for other API errors."""
        client = GeminiClient(api_key="test-key")
        
        mock_response = create_mock_response(status=500, text_data="Internal server error")
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(Exception, match="Gemini API error.*500.*Internal server error"):
                await client.chat.completions.create(
                    messages=[{"role": "user", "content": "Test"}]
                )
    
    async def test_create_handles_malformed_response(self):
        """Test that create() raises error for malformed Gemini response."""
        client = GeminiClient(api_key="test-key")
        
        # Missing required fields in response
        mock_response_data = {
            "candidates": []
        }
        
        mock_response = create_mock_response(status=200, json_data=mock_response_data)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(Exception, match="Unexpected Gemini response format"):
                await client.chat.completions.create(
                    messages=[{"role": "user", "content": "Test"}]
                )
    
    async def test_create_with_empty_messages(self):
        """Test that create() handles empty messages list."""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Response"}]
                }
            }],
            "usageMetadata": {
                "totalTokenCount": 5
            }
        }
        
        mock_response = create_mock_response(status=200, json_data=mock_response_data)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = await client.chat.completions.create(
                messages=[]
            )
            
            # Should handle empty messages gracefully
            assert response.choices[0].message.content == "Response"
    
    async def test_create_with_missing_usage_metadata(self):
        """Test that create() handles missing usage metadata in response."""
        client = GeminiClient(api_key="test-key")
        
        # Response without usageMetadata
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Response without usage data"}]
                }
            }]
        }
        
        mock_response = create_mock_response(status=200, json_data=mock_response_data)
        mock_session = create_mock_session(mock_response)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = await client.chat.completions.create(
                messages=[{"role": "user", "content": "Test"}]
            )
            
            # Should default to 0 tokens when metadata is missing
            assert response.usage.total_tokens == 0
            assert response.choices[0].message.content == "Response without usage data"


@pytest.mark.asyncio
class TestMessageConversion:
    """Test suite for message format conversion."""
    
    def test_convert_simple_user_message(self):
        """Test conversion of a simple user message."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        messages = [{"role": "user", "content": "Hello"}]
        gemini_messages = completions._convert_messages(messages)
        
        assert len(gemini_messages) == 1
        assert gemini_messages[0] == {"parts": [{"text": "Hello"}]}
    
    def test_convert_system_message_prepended_to_user(self):
        """Test that system message is prepended to first user message."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]
        gemini_messages = completions._convert_messages(messages)
        
        assert len(gemini_messages) == 1
        assert "You are helpful" in gemini_messages[0]["parts"][0]["text"]
        assert "Hello" in gemini_messages[0]["parts"][0]["text"]
    
    def test_convert_system_message_only_prepended_once(self):
        """Test that system message is only prepended to first user message."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Second message"}
        ]
        gemini_messages = completions._convert_messages(messages)
        
        assert len(gemini_messages) == 3
        # System message in first user message
        assert "You are helpful" in gemini_messages[0]["parts"][0]["text"]
        assert "First message" in gemini_messages[0]["parts"][0]["text"]
        # System message NOT in second user message
        assert gemini_messages[2]["parts"][0]["text"] == "Second message"
    
    def test_convert_assistant_messages(self):
        """Test conversion of assistant messages."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        gemini_messages = completions._convert_messages(messages)
        
        assert len(gemini_messages) == 2
        assert gemini_messages[0] == {"parts": [{"text": "Hello"}]}
        assert gemini_messages[1] == {"parts": [{"text": "Hi there!"}]}
    
    def test_convert_empty_messages_list(self):
        """Test conversion of empty messages list."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        messages = []
        gemini_messages = completions._convert_messages(messages)
        
        assert gemini_messages == []


@pytest.mark.asyncio
class TestResponseConversion:
    """Test suite for response format conversion."""
    
    def test_convert_simple_response(self):
        """Test conversion of a simple Gemini response."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        gemini_response = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Hello! How can I help?"}]
                }
            }],
            "usageMetadata": {
                "totalTokenCount": 20
            }
        }
        
        response = completions._convert_response(gemini_response)
        
        assert response.choices[0].message.content == "Hello! How can I help?"
        assert response.choices[0].message.role == "assistant"
        assert response.choices[0].finish_reason == "stop"
        assert response.usage.total_tokens == 20
        assert response.usage.prompt_tokens == 0
        assert response.usage.completion_tokens == 20
    
    def test_convert_response_without_usage_metadata(self):
        """Test conversion when usageMetadata is missing."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        gemini_response = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Response"}]
                }
            }]
        }
        
        response = completions._convert_response(gemini_response)
        
        assert response.choices[0].message.content == "Response"
        assert response.usage.total_tokens == 0
    
    def test_convert_response_with_missing_candidates(self):
        """Test that conversion raises error when candidates are missing."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        gemini_response = {"candidates": []}
        
        with pytest.raises(Exception, match="Unexpected Gemini response format"):
            completions._convert_response(gemini_response)
    
    def test_convert_response_with_missing_content(self):
        """Test that conversion raises error when content is missing."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        gemini_response = {
            "candidates": [{
                "content": {}
            }]
        }
        
        with pytest.raises(Exception, match="Unexpected Gemini response format"):
            completions._convert_response(gemini_response)
    
    def test_convert_response_with_missing_parts(self):
        """Test that conversion raises error when parts are missing."""
        client = GeminiClient(api_key="test-key")
        completions = client.chat.completions
        
        gemini_response = {
            "candidates": [{
                "content": {
                    "parts": []
                }
            }]
        }
        
        with pytest.raises(Exception, match="Unexpected Gemini response format"):
            completions._convert_response(gemini_response)
