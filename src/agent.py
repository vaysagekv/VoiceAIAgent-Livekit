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
from livekit.plugins import openai

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
    
    # Create agent session with voice pipeline using HuggingFace Inference API
    # NOTE: Using HuggingFace models via OpenAI-compatible API
    # Set HF_API_KEY in your environment variables
    hf_api_key = os.getenv("HF_API_KEY")
    if not hf_api_key:
        raise ValueError(
            "HF_API_KEY environment variable is required. "
            "Get your token from https://huggingface.co/settings/tokens"
        )

    # HuggingFace Inference API base URL (Router API)
    hf_base_url = "https://router.huggingface.co/v1"

    session = AgentSession(
        stt=openai.STT(
            model="openai/whisper-large-v3",  # HuggingFace Whisper model
            api_key=hf_api_key,
            base_url=hf_base_url,
            language="en",
        ),
        llm=openai.LLM(
            model="meta-llama/Llama-3.1-8B-Instruct",  # or microsoft/DialoGPT-medium, mistralai/Mistral-7B-Instruct
            api_key=hf_api_key,
            base_url=hf_base_url,
            temperature=0.7,
            max_completion_tokens=256,
        ),
        tts=openai.TTS(
            model="espnet/fairseq_tts",  # Note: HF OpenAI-compatible API has limited TTS support
            api_key=hf_api_key,
            base_url=hf_base_url,
            voice="default",
        ),
        vad=silero.VAD.load(),
        # NOTE: Removed MultilingualModel() as it requires LiveKit Cloud Inference
        # Using VAD-based turn detection instead (built into AgentSession when turn_detection is not specified)
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
