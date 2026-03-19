"""Call Attending Agent for handling inbound phone calls after business hours.

This agent attends calls to a specific number after a configurable time (default 5 PM),
greets callers, records their requirements, and logs call details to JSON.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4
from weakref import WeakKeyDictionary

from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    RunContext,
    get_job_context,
    room_io,
)
from livekit.agents.beta.tools import EndCallTool
from livekit.plugins import noise_cancellation, silero
from livekit.plugins import groq, cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Global storage for session data (since JobContext doesn't have userdata)
# Using WeakKeyDictionary to avoid memory leaks
_session_data_store: WeakKeyDictionary = WeakKeyDictionary()

load_dotenv(".env.local")

logger = logging.getLogger("call-attending-agent")
logger.setLevel(logging.INFO)

# Configuration
CALL_ATTEND_AFTER_HOUR = int(os.getenv("CALL_ATTEND_AFTER_HOUR", "17"))  # 5 PM default
AGENT_NAME = os.getenv("CALL_ATTEND_AGENT_NAME", "Tina")
ENABLE_LOGGING = os.getenv("CALL_ATTEND_ENABLE_LOGGING", "true").lower() == "true"
LOGS_DIR = os.getenv("CALL_ATTEND_LOGS_DIR", "calllogs")


class CallAttendingAgent(Agent):
    """AI agent that attends inbound calls after business hours.
    
    Greets callers, records their requirements, and generates call summaries.
    """

    def __init__(self) -> None:
        # Initialize EndCallTool with custom instructions
        end_call_tool = EndCallTool(
            extra_description="Only end the call after the caller has explained their requirement and you have acknowledged it.",
            delete_room=True,
            end_instructions=f"Thank the caller for contacting us. Let them know their request has been recorded and we will get back to them soon.",
        )
        
        super().__init__(
            instructions=f"""You are {AGENT_NAME}, an AI call attending agent. You handle inbound phone calls after business hours.

Your greeting:
- Start with: "I am AI agent {AGENT_NAME} talking. Please tell your requirement. I will record it."

Your behavior:
- Listen carefully to the caller's requirement
- Ask clarifying questions if needed
- Acknowledge their request and confirm you have recorded it
- Be professional, polite, and helpful
- Keep responses concise and clear
- Do not make promises about specific response times or actions
- Record all details of the caller's request

When ending the call:
- Thank the caller for their time
- Confirm their request has been recorded
- Use the end_call tool to hang up gracefully

Remember: This is a voice conversation. Keep responses short enough to say in 10-15 seconds.""",
            tools=end_call_tool.tools,
        )

    async def on_enter(self):
        """Called when the agent enters the session."""
        # Generate the greeting when the agent starts
        await self.session.generate_reply(
            instructions=f"Greet the caller with: 'I am AI agent {AGENT_NAME} talking. Please tell your requirement. I will record it.'"
        )


def is_sip_participant(participant) -> bool:
    """Check if participant is a SIP participant (phone caller).
    
    Args:
        participant: Room participant to check
        
    Returns:
        True if SIP participant, False otherwise
    """
    try:
        # Try direct enum comparison
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            return True
        
        # Try value comparison for compatibility
        if hasattr(participant.kind, 'value'):
            if participant.kind.value == rtc.ParticipantKind.PARTICIPANT_KIND_SIP.value:
                return True
        
        # Try string comparison as fallback
        kind_str = str(participant.kind).lower()
        if 'sip' in kind_str:
            return True
            
    except Exception:
        pass
    
    return False


def get_caller_phone_number(ctx: agents.JobContext) -> Optional[str]:
    """Extract caller's phone number from room participants.
    
    When testing from web browser, returns a dummy phone number.
    
    Args:
        ctx: JobContext with room information
        
    Returns:
        Phone number if found, dummy number for browser testing, None if error
    """
    try:
        has_sip_participant = False
        
        # Look for SIP participants (phone callers)
        for participant in ctx.room.remote_participants.values():
            if is_sip_participant(participant):
                has_sip_participant = True
                
                # Try to get phone number from attributes
                phone = participant.attributes.get("phone_number")
                if phone:
                    return phone
                
                # Try to extract from participant identity or metadata
                phone = participant.attributes.get("sip.callFrom")
                if phone:
                    return phone
                
                # Fallback to participant identity
                if participant.identity:
                    return participant.identity
        
        # Check metadata if available
        if ctx.job.metadata:
            try:
                metadata = json.loads(ctx.job.metadata)
                phone = metadata.get("phone_number")
                if phone:
                    return phone
            except json.JSONDecodeError:
                pass
        
        # If no SIP participant found, this is likely a web browser test
        # Return a dummy phone number for testing
        if not has_sip_participant:
            logger.info("No SIP participant detected - using dummy phone number for browser testing")
            return "+00000000000"
                
    except Exception as e:
        logger.error(f"Error extracting phone number: {e}")
        # Return dummy number on error for graceful handling
        return "+00000000000"
    
    return None


def get_participant_type(ctx: agents.JobContext) -> str:
    """Determine if the caller is from a phone (SIP) or web browser.
    
    Args:
        ctx: JobContext with room information
        
    Returns:
        "phone" for SIP participants, "browser" for web participants
    """
    try:
        for participant in ctx.room.remote_participants.values():
            if is_sip_participant(participant):
                return "phone"
    except Exception:
        pass
    
    return "browser"


def is_after_hours() -> bool:
    """Check if current time is after the configured threshold.
    
    Returns:
        True if current hour >= CALL_ATTEND_AFTER_HOUR, False otherwise
    """
    now = datetime.now()
    return now.hour >= CALL_ATTEND_AFTER_HOUR


def save_call_log(
    room_name: str,
    phone_number: Optional[str],
    start_time: datetime,
    end_time: datetime,
    transcript: list,
    call_summary: str,
    status: str = "completed"
) -> str:
    """Save call details to JSON file.
    
    Args:
        room_name: Name of the room
        phone_number: Caller's phone number
        start_time: Call start time
        end_time: Call end time
        transcript: Full conversation transcript
        call_summary: Generated summary of the call
        status: Call status (completed, rejected_after_hours, etc.)
        
    Returns:
        Path to the saved log file
    """
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{LOGS_DIR}/call_log_{timestamp}_{room_name}.json"
    
    # Calculate duration
    duration_seconds = int((end_time - start_time).total_seconds())
    
    # Build log entry
    log_entry = {
        "call_id": str(uuid4()),
        "room_name": room_name,
        "phone_number": phone_number or "unknown",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "agent_name": AGENT_NAME,
        "call_summary": call_summary,
        "full_transcript": transcript,
        "status": status,
        "call_attend_threshold_hour": CALL_ATTEND_AFTER_HOUR,
    }
    
    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(log_entry, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Call log saved to {filename}")
    return filename


async def generate_call_summary(session: AgentSession) -> str:
    """Generate a summary of the call from session history.
    
    Args:
        session: The agent session with conversation history
        
    Returns:
        Generated summary string
    """
    try:
        # Get conversation history from session.history.items
        history = []
        if hasattr(session, 'history') and hasattr(session.history, 'items'):
            for item in session.history.items:
                if item.type == "message":
                    role = getattr(item, 'role', 'unknown')
                    content = item.text_content if hasattr(item, 'text_content') else str(getattr(item, 'content', ''))
                    history.append(f"{role}: {content}")
                elif item.type == "function_call":
                    history.append(f"function_call: {item.name}")
                elif item.type == "function_call_output":
                    history.append(f"function_output: {item.name}")
        
        if not history:
            return "No conversation recorded."
        
        # For now, return a simple summary based on history
        # In production, you might want to call the LLM explicitly
        main_topic = history[-1] if history else 'N/A'
        return f"Call recorded with {len(history)} messages. Main topic: {main_topic}"
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return "Summary generation failed."


# Create the agent server
server = AgentServer()


def on_session_end_handler(ctx: agents.JobContext):
    """Handler for session end - creates async task for cleanup."""
    return asyncio.create_task(handle_session_end(ctx))


def get_noise_canceller(params):
    """Return appropriate noise canceller based on participant type."""
    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        return noise_cancellation.BVCTelephony()
    else:
        return noise_cancellation.BVC()


@server.rtc_session(
    agent_name="call-attending-agent",
    on_session_end=on_session_end_handler
)
async def call_attending_agent_entry(ctx: agents.JobContext):
    """Entry point for the call attending agent."""
    
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info(f"Call attending agent started for room: {ctx.room.name}")
    
    # Record call start time
    call_start_time = datetime.now()
    
    # Check if after hours
    if not is_after_hours():
        logger.info(f"Call received before {CALL_ATTEND_AFTER_HOUR}:00, politely declining")
        
        # Create temporary session to decline the call
        temp_session = AgentSession(
            stt=groq.STT(model="whisper-large-v3-turbo", language="en"),
            llm=groq.LLM(model="llama-3.3-70b-versatile"),
            tts=cartesia.TTS(model="sonic-3"),
            vad=silero.VAD.load(),
        )
        
        # Start session and politely decline
        await temp_session.start(
            room=ctx.room,
            agent=Agent(
                instructions="You are a polite assistant. Inform the caller that our office is currently open and they should call back during business hours. Keep it brief."
            ),
        )
        
        await temp_session.generate_reply(
            instructions=f"Politely tell the caller: 'Thank you for calling. Our office is currently open. Please call back during business hours before {CALL_ATTEND_AFTER_HOUR}:00. Goodbye.'"
        )
        
        # Wait a moment then end
        await asyncio.sleep(3)
        
        # Close the session - handle if close method doesn't exist
        try:
            if hasattr(temp_session, 'close'):
                await temp_session.close()
            elif hasattr(temp_session, 'aclose'):
                await temp_session.aclose()
            else:
                # If no close method, session will be garbage collected
                logger.debug("No close method available on session, letting it cleanup naturally")
        except Exception as e:
            logger.debug(f"Error closing temporary session: {e}")
        
        # Save rejection log
        phone = get_caller_phone_number(ctx) or "+00000000000"
        save_call_log(
            room_name=ctx.room.name,
            phone_number=phone,
            start_time=call_start_time,
            end_time=datetime.now(),
            transcript=[],
            call_summary="Call declined - received before business hours threshold",
            status="rejected_after_hours"
        )
        
        return
    
    # Extract caller phone number
    phone_number = get_caller_phone_number(ctx)
    participant_type = get_participant_type(ctx)
    
    if phone_number:
        logger.info(f"Incoming call from: {phone_number} (type: {participant_type})")
    else:
        logger.warning("Could not extract caller phone number, using default")
        phone_number = "+00000000000"
    
    # Get API keys
    groq_api_key = os.getenv("GROQ_API_KEY")
    cartesia_api_key = os.getenv("CARTESIA_API_KEY")
    
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is required.")
    
    # Get model configurations
    groq_stt_model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
    groq_llm_model = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
    cartesia_tts_model = os.getenv("CARTESIA_TTS_MODEL", "sonic-3")
    cartesia_tts_voice = os.getenv("CARTESIA_TTS_VOICE", "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")
    
    # Create agent session with optimizations
    session = AgentSession(
        stt=groq.STT(
            model=groq_stt_model,
            language="en",
        ),
        llm=groq.LLM(
            model=groq_llm_model,
            temperature=0.7,
            max_completion_tokens=256,
        ),
        tts=cartesia.TTS(
            model=cartesia_tts_model,
            voice=cartesia_tts_voice,
            language="en",
            api_key=cartesia_api_key,
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        preemptive_generation=True,  # Faster response times
    )
    
    # Store session data for later retrieval using global store
    # (JobContext doesn't have userdata attribute)
    try:
        _session_data_store[ctx] = {
            "call_start_time": call_start_time,
            "phone_number": phone_number,
            "session": session,
            "participant_type": participant_type,
        }
    except Exception as e:
        logger.warning(f"Could not store session data: {e}")
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=CallAttendingAgent(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=get_noise_canceller,
            ),
            close_on_disconnect=True,  # Auto-close when caller hangs up
        ),
    )
    
    # Session runs in the background - wait for it to complete
    # The on_session_end callback will handle cleanup when the session closes
    try:
        await session
    except asyncio.CancelledError:
        logger.info("Session cancelled")
    except Exception as e:
        logger.error(f"Session error: {e}")


async def handle_session_end(ctx: agents.JobContext):
    """Handle session end - save call log and generate summary.
    
    This callback is triggered when the session ends.
    """
    logger.info(f"Session ending for room: {ctx.room.name}")
    
    if not ENABLE_LOGGING:
        logger.info("Call logging disabled")
        return
    
    try:
        # Retrieve stored session data from global store
        session_data = _session_data_store.get(ctx, {})
        call_start_time = session_data.get("call_start_time", datetime.now())
        phone_number = session_data.get("phone_number", "+00000000000")
        session = session_data.get("session")
        participant_type = session_data.get("participant_type", "unknown")
        
        call_end_time = datetime.now()
        
        # Generate session report if available
        transcript_data = []
        try:
            report = ctx.make_session_report()
            if report and hasattr(report, 'to_dict'):
                report_dict = report.to_dict()
                # Extract history from the report dictionary
                history = report_dict.get('history', [])
                for item in history:
                    if isinstance(item, dict):
                        transcript_data.append({
                            "role": item.get('role', 'unknown'),
                            "content": item.get('content', ''),
                            "type": item.get('type', 'unknown'),
                            "timestamp": item.get('timestamp'),
                        })
                    else:
                        transcript_data.append({
                            "role": getattr(item, 'role', 'unknown'),
                            "content": str(getattr(item, 'content', '')),
                            "type": getattr(item, 'type', 'unknown'),
                            "timestamp": getattr(item, 'timestamp', None),
                        })
                logger.info(f"Session report generated with {len(transcript_data)} transcript items")
            else:
                logger.warning("Session report has no history or to_dict method")
        except Exception as e:
            logger.error(f"Error making session report: {e}")
            
        # Fallback: try to get transcript directly from session if report failed
        if not transcript_data and session:
            try:
                if hasattr(session, 'history') and hasattr(session.history, 'items'):
                    for item in session.history.items:
                        if item.type == "message":
                            transcript_data.append({
                                "role": getattr(item, 'role', 'unknown'),
                                "content": item.text_content if hasattr(item, 'text_content') else str(getattr(item, 'content', '')),
                                "type": "message",
                            })
                        elif item.type == "function_call":
                            transcript_data.append({
                                "role": "assistant",
                                "content": f"[Called function: {item.name}]",
                                "type": "function_call",
                            })
                logger.info(f"Fallback: extracted {len(transcript_data)} items from session.history")
            except Exception as e2:
                logger.error(f"Fallback transcript extraction failed: {e2}")
        
        # Generate summary
        call_summary = await generate_call_summary(session) if session else "No summary available"
        
        # Save call log
        log_path = save_call_log(
            room_name=ctx.room.name,
            phone_number=phone_number or "+00000000000",
            start_time=call_start_time,
            end_time=call_end_time,
            transcript=transcript_data,
            call_summary=call_summary,
            status=f"completed_{participant_type}"
        )
        
        logger.info(f"Call log saved: {log_path}")
        
        # Clean up session data
        try:
            if ctx in _session_data_store:
                del _session_data_store[ctx]
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Error in session end handler: {e}")


if __name__ == "__main__":
    agents.cli.run_app(server)