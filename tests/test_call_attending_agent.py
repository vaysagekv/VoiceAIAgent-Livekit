"""Tests for the Call Attending Agent behavior.

These tests validate the CallAttendingAgent implementation
following LiveKit's testing best practices.
"""

import os
import sys
import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.call_attending_agent import (
    CallAttendingAgent,
    get_caller_phone_number,
    is_after_hours,
    save_call_log,
    generate_call_summary,
    CALL_ATTEND_AFTER_HOUR,
    AGENT_NAME,
    LOGS_DIR,
)


class TestCallAttendingAgent:
    """Test suite for the Call Attending Agent."""

    def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        agent = CallAttendingAgent()
        
        # Verify agent is created with instructions
        assert agent.instructions is not None
        assert len(agent.instructions) > 0
        
        # Verify instructions contain expected content
        instructions = agent.instructions.lower()
        assert AGENT_NAME.lower() in instructions
        assert "call attending" in instructions or "inbound" in instructions
        assert "greeting" in instructions or "i am ai agent" in instructions

    def test_agent_has_tools(self):
        """Test that the agent has tools from EndCallTool."""
        agent = CallAttendingAgent()
        
        # The EndCallTool is passed to the agent's tools parameter in __init__
        # Check that the agent was initialized with tools
        tools = getattr(agent, 'tools', None)
        
        # Agent should have tools from EndCallTool
        assert tools is not None, "Agent should have tools initialized"
        assert len(tools) > 0, "Agent should have at least one tool (EndCallTool)"
        
        # Verify it's a list of tools (FunctionTool objects from EndCallTool)
        assert isinstance(tools, list), "Tools should be a list"
        
        # The EndCallTool provides tools for ending the call
        # Just verify we have the tools - actual functionality is tested in integration
        tools_str = str(tools)
        assert "functiontool" in tools_str.lower() or "tool" in tools_str.lower(), \
            "Agent should have function tools"

    def test_agent_instructions_include_greeting(self):
        """Test that instructions include the required greeting."""
        agent = CallAttendingAgent()
        
        instructions = agent.instructions
        
        # Should have the exact greeting phrase
        expected_greeting = f"I am AI agent {AGENT_NAME} talking. Please tell your requirement. I will record it."
        assert expected_greeting in instructions, f"Instructions should contain the greeting: {expected_greeting}"

    def test_agent_instructions_include_behavior_guidance(self):
        """Test that instructions guide agent behavior."""
        agent = CallAttendingAgent()
        
        instructions = agent.instructions.lower()
        
        # Should have behavior guidance
        assert any(phrase in instructions for phrase in [
            "listen", "record", "requirement", "professional"
        ]), "Instructions should include behavior guidance"

    def test_agent_instructions_include_ending_guidance(self):
        """Test that instructions guide call ending."""
        agent = CallAttendingAgent()
        
        instructions = agent.instructions.lower()
        
        # Should have call ending guidance
        assert any(phrase in instructions for phrase in [
            "end_call", "thank", "goodbye", "recorded"
        ]), "Instructions should include call ending guidance"

    def test_agent_instructions_are_voice_optimized(self):
        """Test that instructions are optimized for voice conversation."""
        agent = CallAttendingAgent()
        
        instructions = agent.instructions.lower()
        
        # Should emphasize concise responses
        assert any(phrase in instructions for phrase in [
            "short", "concise", "brief", "10-15 seconds", "voice"
        ]), "Instructions should be optimized for voice"


class TestTimeBasedCallAcceptance:
    """Test time-based call acceptance logic."""

    @patch('src.call_attending_agent.datetime')
    def test_is_after_hours_before_threshold(self, mock_datetime):
        """Test that calls before threshold are rejected."""
        from src.call_attending_agent import is_after_hours
        
        # Set time to 3 PM (15:00) when threshold is 5 PM (17:00)
        mock_now = MagicMock()
        mock_now.hour = 15
        mock_datetime.now.return_value = mock_now
        
        result = is_after_hours()
        assert result is False, "Should return False for times before threshold"

    @patch('src.call_attending_agent.datetime')
    def test_is_after_hours_at_threshold(self, mock_datetime):
        """Test that calls at threshold are accepted."""
        from src.call_attending_agent import is_after_hours
        
        # Set time to exactly 5 PM (17:00)
        mock_now = MagicMock()
        mock_now.hour = 17
        mock_datetime.now.return_value = mock_now
        
        result = is_after_hours()
        assert result is True, "Should return True for times at threshold"

    @patch('src.call_attending_agent.datetime')
    def test_is_after_hours_after_threshold(self, mock_datetime):
        """Test that calls after threshold are accepted."""
        from src.call_attending_agent import is_after_hours
        
        # Set time to 8 PM (20:00)
        mock_now = MagicMock()
        mock_now.hour = 20
        mock_datetime.now.return_value = mock_now
        
        result = is_after_hours()
        assert result is True, "Should return True for times after threshold"

    @patch('src.call_attending_agent.datetime')
    def test_is_after_hours_midnight(self, mock_datetime):
        """Test that calls at midnight are accepted."""
        from src.call_attending_agent import is_after_hours
        
        # Set time to midnight (00:00)
        mock_now = MagicMock()
        mock_now.hour = 0
        mock_datetime.now.return_value = mock_now
        
        result = is_after_hours()
        assert result is False, "Should return False for midnight (before threshold)"


class TestPhoneNumberExtraction:
    """Test phone number extraction from SIP participants."""

    def test_get_caller_phone_number_from_sip_attributes(self):
        """Test extracting phone number from SIP participant attributes."""
        from livekit import rtc
        
        # Create mock context
        mock_ctx = MagicMock()
        mock_participant = MagicMock()
        # Set up participant.kind to match SIP enum
        mock_participant.kind = rtc.ParticipantKind.PARTICIPANT_KIND_SIP
        mock_participant.attributes = {"phone_number": "+15551234567"}
        mock_participant.identity = "sip:+15551234567"
        
        mock_ctx.room.remote_participants = {"sip1": mock_participant}
        mock_ctx.job.metadata = None
        
        result = get_caller_phone_number(mock_ctx)
        assert result == "+15551234567"

    def test_get_caller_phone_number_from_sip_callfrom(self):
        """Test extracting phone number from sip.callFrom attribute."""
        from livekit import rtc
        
        mock_ctx = MagicMock()
        mock_participant = MagicMock()
        # Set up participant.kind to match SIP enum
        mock_participant.kind = rtc.ParticipantKind.PARTICIPANT_KIND_SIP
        mock_participant.attributes = {"sip.callFrom": "+15559876543"}
        mock_participant.identity = "sip:+15559876543"
        
        mock_ctx.room.remote_participants = {"sip1": mock_participant}
        mock_ctx.job.metadata = None
        
        result = get_caller_phone_number(mock_ctx)
        assert result == "+15559876543"

    def test_get_caller_phone_number_from_identity(self):
        """Test extracting phone number from participant identity."""
        from livekit import rtc
        
        mock_ctx = MagicMock()
        mock_participant = MagicMock()
        # Set up participant.kind to match SIP enum
        mock_participant.kind = rtc.ParticipantKind.PARTICIPANT_KIND_SIP
        mock_participant.attributes = {}
        mock_participant.identity = "+15551112222"
        
        mock_ctx.room.remote_participants = {"sip1": mock_participant}
        mock_ctx.job.metadata = None
        
        result = get_caller_phone_number(mock_ctx)
        assert result == "+15551112222"

    def test_get_caller_phone_number_from_metadata(self):
        """Test extracting phone number from job metadata."""
        mock_ctx = MagicMock()
        mock_ctx.room.remote_participants = {}
        mock_ctx.job.metadata = '{"phone_number": "+15553334444"}'
        
        result = get_caller_phone_number(mock_ctx)
        assert result == "+15553334444"

    def test_get_caller_phone_number_not_found(self):
        """Test when phone number cannot be extracted."""
        mock_ctx = MagicMock()
        mock_ctx.room.remote_participants = {}
        mock_ctx.job.metadata = None
        
        result = get_caller_phone_number(mock_ctx)
        assert result is None

    def test_get_caller_phone_number_standard_participant(self):
        """Test that standard (non-SIP) participants are ignored."""
        mock_ctx = MagicMock()
        mock_participant = MagicMock()
        mock_participant.kind = MagicMock()
        mock_participant.kind.value = 0  # PARTICIPANT_KIND_STANDARD
        mock_participant.attributes = {"phone_number": "+15551234567"}
        
        mock_ctx.room.remote_participants = {"user1": mock_participant}
        mock_ctx.job.metadata = None
        
        result = get_caller_phone_number(mock_ctx)
        assert result is None


class TestCallLogSaving:
    """Test call log saving functionality."""

    def test_save_call_log_creates_directory(self, tmp_path):
        """Test that save_call_log creates the logs directory."""
        from src.call_attending_agent import save_call_log
        
        # Create a temporary directory for testing
        test_logs_dir = str(tmp_path / "test_logs")
        
        with patch('src.call_attending_agent.LOGS_DIR', test_logs_dir):
            save_call_log(
                room_name="test-room",
                phone_number="+15551234567",
                start_time=datetime.now(),
                end_time=datetime.now(),
                transcript=[],
                call_summary="Test summary",
                status="completed"
            )
            
            assert os.path.exists(test_logs_dir)

    def test_save_call_log_file_format(self, tmp_path):
        """Test that save_call_log creates properly formatted JSON."""
        from src.call_attending_agent import save_call_log
        
        test_logs_dir = str(tmp_path / "test_logs")
        
        with patch('src.call_attending_agent.LOGS_DIR', test_logs_dir):
            start_time = datetime(2026, 3, 19, 17, 30, 0)
            end_time = datetime(2026, 3, 19, 17, 35, 0)
            
            filepath = save_call_log(
                room_name="test-room-123",
                phone_number="+15551234567",
                start_time=start_time,
                end_time=end_time,
                transcript=[{"role": "user", "content": "Hello"}],
                call_summary="Test call summary",
                status="completed"
            )
            
            # Verify file exists
            assert os.path.exists(filepath)
            
            # Verify JSON structure
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            assert "call_id" in data
            assert "room_name" in data
            assert "phone_number" in data
            assert "start_time" in data
            assert "end_time" in data
            assert "duration_seconds" in data
            assert "agent_name" in data
            assert "call_summary" in data
            assert "full_transcript" in data
            assert "status" in data
            assert "call_attend_threshold_hour" in data
            
            # Verify values
            assert data["room_name"] == "test-room-123"
            assert data["phone_number"] == "+15551234567"
            assert data["duration_seconds"] == 300  # 5 minutes
            assert data["agent_name"] == AGENT_NAME
            assert data["status"] == "completed"
            assert data["call_summary"] == "Test call summary"

    def test_save_call_log_with_unknown_phone(self, tmp_path):
        """Test that save_call_log handles unknown phone numbers."""
        from src.call_attending_agent import save_call_log
        
        test_logs_dir = str(tmp_path / "test_logs")
        
        with patch('src.call_attending_agent.LOGS_DIR', test_logs_dir):
            filepath = save_call_log(
                room_name="test-room",
                phone_number=None,
                start_time=datetime.now(),
                end_time=datetime.now(),
                transcript=[],
                call_summary="Test",
                status="completed"
            )
            
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            assert data["phone_number"] == "unknown"


class TestConfiguration:
    """Test configuration settings."""

    @patch.dict(os.environ, {"CALL_ATTEND_AFTER_HOUR": "18"})
    def test_call_attend_after_hour_custom(self):
        """Test custom CALL_ATTEND_AFTER_HOUR setting."""
        # Reload module to pick up new env var
        import importlib
        from src import call_attending_agent
        importlib.reload(call_attending_agent)
        
        assert call_attending_agent.CALL_ATTEND_AFTER_HOUR == 18

    @patch.dict(os.environ, {"CALL_ATTEND_AGENT_NAME": "Alex"})
    def test_agent_name_custom(self):
        """Test custom CALL_ATTEND_AGENT_NAME setting."""
        import importlib
        from src import call_attending_agent
        importlib.reload(call_attending_agent)
        
        assert call_attending_agent.AGENT_NAME == "Alex"

    @patch.dict(os.environ, {"CALL_ATTEND_ENABLE_LOGGING": "false"})
    def test_enable_logging_false(self):
        """Test disabling call logging."""
        import importlib
        from src import call_attending_agent
        importlib.reload(call_attending_agent)
        
        assert call_attending_agent.ENABLE_LOGGING is False

    @patch.dict(os.environ, {"CALL_ATTEND_LOGS_DIR": "custom_logs"})
    def test_logs_dir_custom(self):
        """Test custom logs directory."""
        import importlib
        from src import call_attending_agent
        importlib.reload(call_attending_agent)
        
        assert call_attending_agent.LOGS_DIR == "custom_logs"

    def test_default_values(self):
        """Test default configuration values."""
        # Clear environment variables
        env_vars = ["CALL_ATTEND_AFTER_HOUR", "CALL_ATTEND_AGENT_NAME", 
                   "CALL_ATTEND_ENABLE_LOGGING", "CALL_ATTEND_LOGS_DIR"]
        original_values = {}
        for var in env_vars:
            original_values[var] = os.environ.pop(var, None)
        
        try:
            import importlib
            from src import call_attending_agent
            importlib.reload(call_attending_agent)
            
            assert call_attending_agent.CALL_ATTEND_AFTER_HOUR == 17
            assert call_attending_agent.AGENT_NAME == "Tina"
            assert call_attending_agent.ENABLE_LOGGING is True
            assert call_attending_agent.LOGS_DIR == "calllogs"
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value


class TestCallSummaryGeneration:
    """Test call summary generation."""

    @pytest.mark.asyncio
    async def test_generate_call_summary_with_history(self):
        """Test summary generation with conversation history."""
        mock_session = MagicMock()
        mock_item = MagicMock()
        mock_item.content = "I need help with my order"
        mock_item.role = "user"
        mock_session.history = [mock_item]
        
        result = await generate_call_summary(mock_session)
        
        assert "1 messages" in result or "messages" in result

    @pytest.mark.asyncio
    async def test_generate_call_summary_empty_history(self):
        """Test summary generation with empty history."""
        mock_session = MagicMock()
        mock_session.history = []
        
        result = await generate_call_summary(mock_session)
        
        assert result == "No conversation recorded."

    @pytest.mark.asyncio
    async def test_generate_call_summary_error_handling(self):
        """Test summary generation error handling."""
        mock_session = MagicMock()
        mock_session.history = None  # This will cause an error
        
        result = await generate_call_summary(mock_session)
        
        assert result == "Summary generation failed."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])