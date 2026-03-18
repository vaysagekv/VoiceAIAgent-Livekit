"""Voice AI Agent for casual phone conversations."""
import asyncio
import json
from typing import Optional

from dotenv import load_dotenv
import os

from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    RunContext,
    function_tool,
    get_job_context,
    room_io,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins import groq, cartesia

load_dotenv(".env.local")


class CasualConversationAgent(Agent):
    """A friendly voice AI agent for casual conversations."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a friendly and engaging voice AI assistant having a casual phone conversation.

Your personality:
- Warm, personable, and genuinely interested in the person you're talking to
- Keep responses concise and natural - avoid reading long responses
- Ask follow-up questions to keep the conversation flowing
- React naturally to what the person says with brief acknowledgments
- If they seem busy or want to end the call, use the end_call tool

Conversation style:
- Start with a friendly greeting and introduction
- Listen actively and respond thoughtfully
- Share brief personal anecdotes when relevant (you're an AI assistant)
- Keep the tone light and positive
- Avoid robotic or overly formal language
- Don't use filler words like "um" or "uh"

When ending the call:
- Be polite and thank them for the conversation
- Use the end_call tool to hang up gracefully

Remember: This is a voice conversation. Keep responses short enough to say in 10-15 seconds.""",
        )

    @function_tool()
    async def end_call(self, context: RunContext) -> str:
        """End the phone call gracefully when the conversation is complete.
        
        Call this when:
        - The user says they need to go or hang up
        - The user says goodbye
        - The user indicates they're busy or can't talk
        - The conversation has naturally concluded
        """
        await context.wait_for_playout()
        await hangup_call()
        return "Call ended successfully."


async def hangup_call() -> None:
    """Hang up the phone call by deleting the room."""
    ctx = get_job_context()
    if ctx is None:
        return
    
    await ctx.api.room.delete_room(
        agents.api.DeleteRoomRequest(
            room=ctx.room.name,
        )
    )


# Create the agent server
server = AgentServer()


@server.rtc_session(agent_name="casual-caller")
async def casual_caller_agent(ctx: agents.JobContext):
    """Entry point for the voice AI agent."""
    
    # Parse metadata for phone call info
    phone_number: Optional[str] = None
    dial_info = {}
    
    try:
        if ctx.job.metadata:
            dial_info = json.loads(ctx.job.metadata)
            phone_number = dial_info.get("phone_number")
    except json.JSONDecodeError:
        pass
    
    # Load configuration from environment
    sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
    caller_display_name = os.getenv("CALLER_DISPLAY_NAME", "AI Assistant")
    
    # Create the outbound call if phone number was provided
    if phone_number and sip_trunk_id:
        try:
            await ctx.api.sip.create_sip_participant(
                agents.api.CreateSIPParticipantRequest(
                    room_name=ctx.room.name,
                    sip_trunk_id=sip_trunk_id,
                    sip_call_to=phone_number,
                    participant_identity=phone_number,
                    participant_name=caller_display_name,
                    display_name=caller_display_name,
                    wait_until_answered=True,
                    krisp_enabled=True,
                    play_dialtone=True,
                )
            )
            print(f"Call to {phone_number} picked up successfully")
        except agents.api.TwirpError as e:
            print(f"Error creating SIP participant: {e.message}")
            print(f"SIP status: {e.metadata.get('sip_status_code')} {e.metadata.get('sip_status')}")
            ctx.shutdown()
            return
    elif phone_number:
        print("Warning: SIP_OUTBOUND_TRUNK_ID not set. Cannot make outbound calls.")
        print("Set your outbound trunk ID in the .env.local file.")
    
    # Load API keys
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable is required. "
            "Get your API key from https://console.groq.com/keys"
        )

    # Get optional model configurations from environment
    groq_stt_model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
    groq_llm_model = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
    
    # Cartesia TTS - Groq discontinued their TTS service
    # Available models: "sonic-3", "sonic-2", "sonic-turbo", "sonic"
    # Available voices: Use voice ID from https://play.cartesia.ai/voices
    # Sample English voices:
    #   - "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc" (Jacqueline - confident American female)
    #   - "a167e0f3-df7e-4d52-a9c3-f949145efdab" (Blake - energetic American male)
    #   - "f786b574-daa5-4673-aa0c-cbe3e8534c02" (Default voice)
    cartesia_tts_model = os.getenv("CARTESIA_TTS_MODEL", "sonic-3")
    cartesia_tts_voice = os.getenv("CARTESIA_TTS_VOICE", "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")

    # Create agent session with Groq for STT/LLM and Cartesia for TTS
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
        ),
        vad=silero.VAD.load(),
    )

    # Start the session with telephony-optimized noise cancellation
    await session.start(
        room=ctx.room,
        agent=CasualConversationAgent(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony() 
                    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP 
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Only greet first if this is NOT an outbound call
    # For outbound calls, let the callee speak first
    if phone_number is None:
        await session.generate_reply(
            instructions="Greet the user warmly and introduce yourself as a voice AI assistant ready to chat."
        )


if __name__ == "__main__":
    agents.cli.run_app(server)
