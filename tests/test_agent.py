"""Tests for the Voice AI Agent behavior.

These tests validate the CasualConversationAgent implementation
following LiveKit's testing best practices.
"""

import os
import sys
import pytest

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.agent import CasualConversationAgent


class TestCasualConversationAgent:
    """Test suite for the Casual Conversation Agent."""

    def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        agent = CasualConversationAgent()
        
        # Verify agent is created with instructions
        assert agent.instructions is not None
        assert len(agent.instructions) > 0
        
        # Verify instructions contain expected content
        assert "friendly" in agent.instructions.lower() or "casual" in agent.instructions.lower()
        assert "voice" in agent.instructions.lower() or "conversation" in agent.instructions.lower()

    def test_agent_has_end_call_tool(self):
        """Test that the agent has the end_call function tool."""
        agent = CasualConversationAgent()
        
        # Check that tools are available - they might be in _tools or tools attribute
        tools = getattr(agent, '_tools', {}) or getattr(agent, 'tools', {})
        
        # Check if end_call tool exists by name
        has_end_call = False
        if isinstance(tools, dict):
            has_end_call = "end_call" in tools
        else:
            # Tools might be a list of FunctionTool objects
            has_end_call = any(
                getattr(t, '__name__', '') == 'end_call' or 
                'end_call' in str(t).lower()
                for t in tools
            )
        
        assert has_end_call, "Agent should have an end_call tool"

    def test_agent_instructions_include_personality(self):
        """Test that instructions define a clear personality."""
        agent = CasualConversationAgent()
        
        instructions = agent.instructions.lower()
        
        # Should have personality guidance
        assert any(word in instructions for word in [
            "personality", "friendly", "warm", "tone", "style"
        ]), "Instructions should define personality"

    def test_agent_instructions_include_conversation_guidance(self):
        """Test that instructions guide conversation behavior."""
        agent = CasualConversationAgent()
        
        instructions = agent.instructions.lower()
        
        # Should have conversation guidance
        assert any(phrase in instructions for phrase in [
            "ask", "respond", "listen", "conversation", "chat"
        ]), "Instructions should include conversation guidance"

    def test_agent_instructions_are_voice_optimized(self):
        """Test that instructions are optimized for voice conversation."""
        agent = CasualConversationAgent()
        
        instructions = agent.instructions.lower()
        
        # Should emphasize concise responses
        assert any(phrase in instructions for phrase in [
            "short", "concise", "brief", "respond", "fast"
        ]), "Instructions should be optimized for voice"

    def test_agent_instructions_prohibit_robotic_language(self):
        """Test that instructions discourage robotic language."""
        agent = CasualConversationAgent()
        
        instructions = agent.instructions.lower()
        
        # Should avoid robotic language
        assert "um" in instructions or "uh" in instructions, \
            "Should explicitly avoid filler words"


class TestPhoneNumberValidation:
    """Test phone number validation logic."""

    def test_valid_us_number_with_plus(self):
        """Test valid US number with + prefix."""
        from src.call_manager import CallManager
        
        manager = CallManager(
            livekit_url="wss://test.livekit.cloud",
            api_key="test-key",
            api_secret="test-secret",
            sip_trunk_id="ST_test"
        )
        
        assert manager.validate_phone_number("+15551234567") is True
        assert manager.validate_phone_number("+1-555-123-4567") is True

    def test_valid_us_number_without_plus(self):
        """Test valid US number without + prefix."""
        from src.call_manager import CallManager
        
        manager = CallManager(
            livekit_url="wss://test.livekit.cloud",
            api_key="test-key",
            api_secret="test-secret",
            sip_trunk_id="ST_test"
        )
        
        assert manager.validate_phone_number("5551234567") is True
        assert manager.validate_phone_number("(555) 123-4567") is True

    def test_valid_international_number(self):
        """Test valid international numbers."""
        from src.call_manager import CallManager
        
        manager = CallManager(
            livekit_url="wss://test.livekit.cloud",
            api_key="test-key",
            api_secret="test-secret",
            sip_trunk_id="ST_test"
        )
        
        # UK number
        assert manager.validate_phone_number("+447911123456") is True

    def test_invalid_number_too_short(self):
        """Test invalid - too short."""
        from src.call_manager import CallManager
        
        manager = CallManager(
            livekit_url="wss://test.livekit.cloud",
            api_key="test-key",
            api_secret="test-secret",
            sip_trunk_id="ST_test"
        )
        
        assert manager.validate_phone_number("+1555") is False

    def test_invalid_number_too_long(self):
        """Test invalid - too long."""
        from src.call_manager import CallManager
        
        manager = CallManager(
            livekit_url="wss://test.livekit.cloud",
            api_key="test-key",
            api_secret="test-secret",
            sip_trunk_id="ST_test"
        )
        
        assert manager.validate_phone_number("+15551234567890123456") is False

    def test_invalid_number_no_digits(self):
        """Test invalid - no digits."""
        from src.call_manager import CallManager
        
        manager = CallManager(
            livekit_url="wss://test.livekit.cloud",
            api_key="test-key",
            api_secret="test-secret",
            sip_trunk_id="ST_test"
        )
        
        assert manager.validate_phone_number("not-a-number") is False


class TestCallManager:
    """Test CallManager functionality."""

    def test_call_manager_requires_credentials(self):
        """Test that CallManager requires credentials when none provided."""
        from src.call_manager import CallManager
        
        # Test with explicit None values (ignores any .env.local file)
        with pytest.raises(ValueError):
            CallManager(
                livekit_url=None,
                api_key=None,
                api_secret=None,
                sip_trunk_id=None,
            )

    def test_call_manager_accepts_credentials(self):
        """Test that CallManager accepts explicit credentials."""
        from src.call_manager import CallManager
        
        manager = CallManager(
            livekit_url="wss://test.livekit.cloud",
            api_key="test-key",
            api_secret="test-secret",
            sip_trunk_id="ST_test"
        )
        
        assert manager.livekit_url == "wss://test.livekit.cloud"
        assert manager.api_key == "test-key"
        assert manager.api_secret == "test-secret"
        assert manager.sip_trunk_id == "ST_test"

    def test_normalize_phone_number(self):
        """Test phone number normalization."""
        from src.call_manager import CallManager
        
        manager = CallManager(
            livekit_url="wss://test.livekit.cloud",
            api_key="test-key",
            api_secret="test-secret",
            sip_trunk_id="ST_test"
        )
        
        # Should add +1 for US numbers
        assert manager._normalize_phone_number("5551234567") == "+15551234567"
        assert manager._normalize_phone_number("15551234567") == "+15551234567"
        
        # Should keep + for international
        assert manager._normalize_phone_number("+447911123456") == "+447911123456"
        
        # Should remove formatting
        assert manager._normalize_phone_number("(555) 123-4567") == "+15551234567"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])