"""
Shared test fixtures and configuration
"""
import sys
import os
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure event loop
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock fixtures
@pytest.fixture
def mock_message_queue():
    """Create a mock message queue"""
    mock = AsyncMock()
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.consume = AsyncMock(return_value=None)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
def mock_agent_registry():
    """Create a mock agent registry"""
    mock = Mock()
    mock.register = Mock()
    mock.unregister = Mock()
    mock.get = Mock(return_value=None)
    mock.list_all = Mock(return_value=[])
    mock.list_by_capability = Mock(return_value=[])
    mock.create_agent = Mock()
    return mock


@pytest.fixture
def mock_agent():
    """Create a mock agent"""
    mock = AsyncMock()
    mock.id = "test-agent-123"
    mock.agent_type = "test"
    mock.status = "ready"
    mock.initialize = AsyncMock()
    mock.terminate = AsyncMock()
    mock.process_message = AsyncMock()
    return mock