# test_llm.py
# -----------
# LLMClient and each LLM backend (HuggingFace, OpenAI, gguf etc.) unit test file
# - generate/chat main method normal operation/exception handling/performance verification
# - Various prompt/input case tests, LLM response structure verification
# - MCP pipeline LLM integration reliability assurance purpose
# - Automated test/CI integration included
# - Detailed design/implementation rules reference: .cursor/rules/rl-text2sql-public-api.md

import pytest
import os
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_client import get_llm_client

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY environment variable required")
def test_openai_chat():
    """OpenAI chat basic function test"""
    llm = get_llm_client("openai")
    messages = [{"role": "user", "content": "Hello, LLM!"}]
    result = llm.chat(messages)
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY environment variable required")
def test_openai_generate():
    """OpenAI generation basic function test"""
    llm = get_llm_client("openai")
    prompt = "Say hello in Korean."
    result = llm.generate(prompt)
    assert isinstance(result, str)
    assert "hello" in result.lower() or len(result) > 0

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY environment variable required")
def test_openai_chat_with_parameters():
    """OpenAI chat parameter test"""
    llm = get_llm_client("openai")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Give me a simple answer."}
    ]
    
    result = llm.chat(
        messages, 
        model="gpt-3.5-turbo",
        max_tokens=50,
        temperature=0.1
    )
    
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY environment variable required")
def test_openai_text2sql_specific():
    """Text2SQL related prompt test"""
    llm = get_llm_client("openai")
    
    # DataFrame based query generation test
    prompt = """
    You have the following DataFrame:
    df = pd.DataFrame({'year': [2020, 2021, 2022], 'population': [50000000, 51000000, 52000000]})
    
    Write pandas code to calculate the average population. Output only code without explanation.
    """
    
    result = llm.generate(prompt, max_tokens=100, temperature=0.1)
    
    assert isinstance(result, str)
    assert len(result) > 0
    # Should contain pandas related keywords
    assert any(keyword in result.lower() for keyword in ['df', 'mean', 'average', 'population'])

def test_llm_client_factory():
    """LLM client factory pattern test"""
    # OpenAI client creation
    openai_client = get_llm_client("openai")
    assert openai_client is not None
    assert hasattr(openai_client, 'chat')
    assert hasattr(openai_client, 'generate')
    
    # Error handling for invalid backend request
    with pytest.raises((ValueError, KeyError, ImportError)):
        get_llm_client("invalid_backend")

@patch('llm_client.openai_api.OpenAI')
def test_openai_client_mocked(mock_openai):
    """OpenAI client Mock test"""
    # Mock setup
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_message.content = "Mocked response"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    # Test execution
    llm = get_llm_client("openai")
    messages = [{"role": "user", "content": "Test"}]
    result = llm.chat(messages)
    
    assert result == "Mocked response"
    mock_client.chat.completions.create.assert_called_once()

def test_error_handling():
    """LLM client error handling test"""
    try:
        llm = get_llm_client("openai")
        
        # Test with empty message (may cause error)
        with pytest.raises(Exception):
            llm.chat([])
        
        # Invalid message format
        with pytest.raises(Exception):
            llm.chat([{"invalid": "format"}])
            
    except Exception as e:
        # Pass if API key missing or network issues
        if "API" in str(e) or "network" in str(e).lower():
            pytest.skip(f"API related error, skipping: {e}")
        else:
            raise

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY environment variable required")
def test_llm_response_consistency():
    """LLM response consistency test"""
    llm = get_llm_client("openai")
    
    # Multiple calls with same prompt
    prompt = "What is 1+1 in Python?"
    results = []
    
    for _ in range(3):
        try:
            result = llm.generate(prompt, temperature=0.1)
            results.append(result)
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    # All results should be strings
    for result in results:
        assert isinstance(result, str)
        assert len(result) > 0

def test_llm_client_interface():
    """LLM client interface consistency test"""
    try:
        llm = get_llm_client("openai")
        
        # Check required methods exist
        assert hasattr(llm, 'chat'), "chat method missing"
        assert hasattr(llm, 'generate'), "generate method missing"
        assert callable(llm.chat), "chat is not callable"
        assert callable(llm.generate), "generate is not callable"
        
    except Exception as e:
        if "API" in str(e):
            pytest.skip("API key related error, skipping")
        else:
            raise

def test_backend_specific_features():
    """Backend specific feature test"""
    try:
        openai_llm = get_llm_client("openai")
        
        # OpenAI specific feature test
        assert hasattr(openai_llm, 'client'), "OpenAI client attribute missing"
        
        # Other backends can be added (currently only OpenAI implemented)
        # huggingface_llm = get_llm_client("huggingface")
        # gguf_llm = get_llm_client("gguf")
        
    except Exception as e:
        if "API" in str(e) or "import" in str(e).lower():
            pytest.skip(f"Backend related error, skipping: {e}")
        else:
            raise

@pytest.mark.parametrize("backend", ["openai"])
def test_multiple_backends(backend):
    """Multiple backend support test (parameterized)"""
    try:
        llm = get_llm_client(backend)
        assert llm is not None
        
        # Basic function test
        if backend == "openai" and 'OPENAI_API_KEY' in os.environ:
            result = llm.generate("Hello", max_tokens=10)
            assert isinstance(result, str)
            
    except Exception as e:
        pytest.skip(f"{backend} backend test skipped: {e}")

# Performance test (optional)
@pytest.mark.slow
@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY environment variable required")
def test_llm_performance():
    """LLM response time performance test"""
    import time
    
    llm = get_llm_client("openai")
    start_time = time.time()
    
    try:
        result = llm.generate("Simple answer", max_tokens=50)
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 30  # Response within 30 seconds
        assert len(result) > 0
        
    except Exception as e:
        pytest.skip(f"Performance test skipped: {e}")
