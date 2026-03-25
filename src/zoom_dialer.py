"""Zoom SIP Dialer for connecting agent to Zoom meetings."""

import asyncio
import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from livekit import agents, api
from livekit.agents import Agent, AgentSession, AgentServer, room_io
from livekit.plugins import groq, cartesia, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.beta.tools import EndCallTool

load_dotenv(".env.local")

logger = logging.getLogger("zoom-dialer")
logger.setLevel(logging.INFO)


class ZoomDialingAgent(Agent):
    """Agent that dials into Zoom meetings via SIP."""

    def __init__(self) -> None:
        end_call_tool = EndCallTool(
            extra_description="End the call when the meeting is finished or user requests it.",
            delete_room=True,
            end_instructions="Thank you. The AI agent is leaving the meeting now.",
        )

        super().__init__(
            instructions="""You are an AI assistant participating in a Zoom meeting via SIP dial-in.

Your greeting when joining:
- Announce: "Hello, this is the AI assistant joining via phone. I'm ready to help."

Your behavior:
- Listen carefully to meeting participants
- Respond professionally and concisely
- Participate in discussions as appropriate
- Keep responses brief (15-20 seconds max)
- Use the end_call tool to leave when the task is complete

Remember: You are on a phone connection in a Zoom meeting. Audio quality may vary.""",
            tools=end_call_tool.tools,
        )

    async def on_enter(self):
        """Called when agent enters the session."""
        await self.session.generate_reply(
            instructions="Introduce yourself briefly as the AI assistant joining via phone."
        )


# Create the agent server
server = AgentServer()


async def dial_zoom_meeting(
    ctx: agents.JobContext,
    meeting_id: str,
    meeting_password: Optional[str] = None,
) -> bool:
    """Dial into a Zoom meeting via SIP.
    
    Args:
        ctx: JobContext for the agent
        meeting_id: Zoom meeting ID (numeric)
        meeting_password: Optional meeting password
        
    Returns:
        True if call was successfully initiated, False otherwise
    """
    trunk_id = os.getenv("ZOOM_SIP_TRUNK_ID")
    if not trunk_id:
        logger.error("ZOOM_SIP_TRUNK_ID not configured in environment")
        return False

    # Construct Zoom SIP URI
    # Format: <meeting-id>@zoomcrc.com
    zoom_sip_uri = f"{meeting_id}@zoomcrc.com"
    
    # If password is provided, append it with # separator
    if meeting_password:
        zoom_sip_uri = f"{meeting_id}.{meeting_password}@zoomcrc.com"

    caller_id_name = os.getenv("ZOOM_CALLER_ID_NAME", "AI Agent")

    logger.info(f"Dialing Zoom meeting: {meeting_id} via SIP")
    
    try:
        # Create SIP participant (initiates the call)
        participant = await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=trunk_id,
                sip_call_to=zoom_sip_uri,
                participant_identity=f"zoom-{meeting_id}",
                participant_name=caller_id_name,
                wait_until_answered=True,
                play_dialtone=True,  # Play dial tone while connecting
            )
        )
        
        logger.info(f"Successfully connected to Zoom meeting: {participant}")
        return True
        
    except api.TwirpError as e:
        sip_code = e.metadata.get('sip_status_code')
        sip_status = e.metadata.get('sip_status')
        logger.error(f"Failed to dial Zoom: SIP {sip_code} - {sip_status}")
        return False
    except Exception as e:
        logger.error(f"Error dialing Zoom meeting: {e}")
        return False


@server.rtc_session(
    agent_name="zoom-dialing-agent",
    on_session_end=lambda ctx: logger.info(f"Session ended: {ctx.room.name}")
)
async def zoom_agent_entry(ctx: agents.JobContext):
    """Entry point for the Zoom dialing agent."""
    
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info(f"Zoom agent started for room: {ctx.room.name}")

    # Get meeting details from metadata
    metadata = {}
    if ctx.job.metadata:
        try:
            metadata = json.loads(ctx.job.metadata)
        except json.JSONDecodeError:
            logger.warning("Could not parse job metadata as JSON")

    meeting_id = metadata.get("meeting_id") or os.getenv("ZOOM_MEETING_ID")
    meeting_password = metadata.get("meeting_password") or os.getenv("ZOOM_MEETING_PASSWORD")

    if not meeting_id:
        logger.error("No Zoom meeting ID provided")
        await ctx.shutdown()
        return

    # Dial into the Zoom meeting
    connected = await dial_zoom_meeting(ctx, meeting_id, meeting_password)
    
    if not connected:
        logger.error("Failed to connect to Zoom meeting")
        await ctx.shutdown()
        return

    # Wait for Zoom participant to join
    try:
        participant = await ctx.wait_for_participant(identity=f"zoom-{meeting_id}")
        logger.info(f"Zoom participant joined: {participant.identity}")
    except Exception as e:
        logger.error(f"Timeout waiting for Zoom participant: {e}")
        await ctx.shutdown()
        return

    # Create agent session
    session = AgentSession(
        stt=groq.STT(model="whisper-large-v3-turbo", language="en"),
        llm=groq.LLM(model="llama-3.3-70b-versatile", temperature=0.7),
        tts=cartesia.TTS(model="sonic-3"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        preemptive_generation=True,
    )

    # Start the session with the Zoom participant
    await session.start(
        room=ctx.room,
        agent=ZoomDialingAgent(),
        room_options=room_io.RoomOptions(
            close_on_disconnect=True,
        ),
    )

    # Wait for session to complete
    try:
        await session
    except asyncio.CancelledError:
        logger.info("Session cancelled")
    except Exception as e:
        logger.error(f"Session error: {e}")


if __name__ == "__main__":
    agents.cli.run_app(server)