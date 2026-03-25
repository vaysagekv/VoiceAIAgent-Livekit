# Connect LiveKit Agent to Zoom Meetings via SIP

This guide explains how to connect your LiveKit Call Attending Agent to Zoom meetings using SIP dial-in. This allows your AI agent to join Zoom meetings as an audio participant, perfect for client demos.

## Architecture Overview

```
┌─────────────────┐     SIP INVITE      ┌─────────────────┐
│  LiveKit Agent  │ ───────────────────> │  Twilio Elastic │
│                 │                      │   SIP Trunk     │
└─────────────────┘                      └─────────────────┘
         │                                        │
         │         SIP via PSTN                   │
         │    ┌──────────────────┐                │
         └───>│   Zoom Meeting   │<───────────────┘
              │ (SIP CRC)        │
              └──────────────────┘
                      ▲
                      │ Join via Zoom Client
                      │
              ┌───────────────┐
              │   Client's    │
              │ Zoom Desktop/ │
              │ Mobile App    │
              └───────────────┘
```

## Prerequisites

- **Twilio Account** with Elastic SIP Trunking enabled
- **LiveKit Cloud** or self-hosted LiveKit server
- **Zoom Account** with H.323/SIP Room Connector (included in most business plans)
- Your LiveKit agent code (`call_attending_agent.py`)

---

## Part 1: Twilio Elastic SIP Trunk Setup

Since we need to dial out to Zoom's SIP infrastructure, we must use **Twilio Elastic SIP Trunking** (not just Programmable Voice).

### Step 1.1: Create an Elastic SIP Trunk

1. Log into [Twilio Console](https://console.twilio.com/)
2. Navigate to **Elastic SIP Trunking** → **Trunks** → **Create New SIP Trunk**
3. Enter a friendly name: `LiveKit-Zoom-Outbound`
4. Click **Create**

### Step 1.2: Configure Origination (Incoming from LiveKit)

1. Click on your new trunk → **Origination** tab
2. Click **Add new Origination URI**
3. Configure:
   - **Origination URI**: Your LiveKit SIP endpoint (format: `sip:<your-sip-endpoint>`)
   - **Priority**: 1
   - **Weight**: 1
   - **Region**: Select closest to your LiveKit deployment

> **Note:** Get your LiveKit SIP endpoint from your LiveKit Cloud dashboard or self-hosted config.

### Step 1.3: Configure Termination (Outgoing to Zoom)

1. Go to the **Termination** tab
2. Configure:
   - **Termination SIP URI**: `sip:zoomcrc.com` (Zoom's SIP domain)
   - **Authentication**: Create IP Access Control List
     - Name: `LiveKit-IPs`
     - Add all LiveKit Cloud IP ranges (see below)
   - **Credential List**: Create username/password for SIP authentication
     - Username: `livekit_zoom_user`
     - Password: Generate a strong password

#### LiveKit Cloud IP Ranges

LiveKit Cloud doesn't have static IPs, so you have two options:

**Option A: Allow All IPs (Less Secure)**
```
0.0.0.0/0
```

**Option B: Restrictive (More Secure)**
Use `0.0.0.0/1` and `128.0.0.0/1` to cover all IPs while maintaining some format validation.

### Step 1.4: Save and Note Credentials

After saving, note down:
- **SIP Trunk Domain**: e.g., `livekit-zoom.pstn.twilio.com`
- **Authentication Username**: e.g., `livekit_zoom_user`
- **Authentication Password**: Your generated password
- **Phone Number**: If you want to assign a number to the trunk (optional for this use case)

---

## Part 2: LiveKit Outbound Trunk Configuration

### Step 2.1: Create Outbound Trunk JSON

Create a file named `outbound-trunk-zoom.json`:

```json
{
  "trunk": {
    "name": "Twilio Zoom Outbound Trunk",
    "address": "livekit-zoom.pstn.twilio.com",
    "numbers": ["*"],
    "authUsername": "livekit_zoom_user",
    "authPassword": "your_twilio_sip_password",
    "transport": "SIP_TRANSPORT_TCP"
  }
}
```

> **Replace**:
> - `livekit-zoom.pstn.twilio.com` with your actual Twilio SIP trunk domain
> - `livekit_zoom_user` with your authentication username
> - `your_twilio_sip_password` with your authentication password

### Step 2.2: Create the Outbound Trunk

Run the LiveKit CLI command:

```bash
lk sip outbound create outbound-trunk-zoom.json
```

You'll receive a SIP Trunk ID like `ST_xxxxx`. **Save this ID** - you'll need it in the agent code.

### Step 2.3: Verify the Trunk

List your outbound trunks to confirm:

```bash
lk sip outbound list
```

---

## Part 3: Agent Code Modifications

### Step 3.1: Environment Variables

Add these to your `.env.local` file:

```env
# Zoom SIP Integration
ZOOM_SIP_TRUNK_ID=ST_xxxxx  # Your outbound trunk ID from Step 2.2
ZOOM_MEETING_ID=1234567890   # Default Zoom meeting ID (optional)
ZOOM_MEETING_PASSWORD=       # Meeting password if required
ZOOM_CALLER_ID_NAME=AI Agent # Display name when joining Zoom
```

### Step 3.2: Create Zoom Dialing Script

Create a new file `src/zoom_dialer.py`:

```python
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
```

### Step 3.3: Update Existing Agent for Zoom Mode (Optional)

If you want to add Zoom dialing capability to your existing `call_attending_agent.py`, add this function:

```python
# Add to call_attending_agent.py

async def dial_zoom_meeting(
    ctx: agents.JobContext,
    meeting_id: str,
    meeting_password: Optional[str] = None,
) -> bool:
    """Dial into a Zoom meeting via SIP."""
    trunk_id = os.getenv("ZOOM_SIP_TRUNK_ID")
    if not trunk_id:
        logger.error("ZOOM_SIP_TRUNK_ID not configured")
        return False

    # Construct Zoom SIP URI
    zoom_sip_uri = f"{meeting_id}@zoomcrc.com"
    if meeting_password:
        # Zoom uses format: meeting_id.password@zoomcrc.com
        zoom_sip_uri = f"{meeting_id}.{meeting_password}@zoomcrc.com"

    try:
        participant = await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=trunk_id,
                sip_call_to=zoom_sip_uri,
                participant_identity=f"zoom-{meeting_id}",
                participant_name=os.getenv("ZOOM_CALLER_ID_NAME", "AI Agent"),
                wait_until_answered=True,
                play_dialtone=True,
            )
        )
        logger.info(f"Connected to Zoom: {participant}")
        return True
    except api.TwirpError as e:
        logger.error(f"SIP Error: {e.metadata.get('sip_status')}")
        return False
```

---

## Part 4: Running the Zoom Agent

### Option A: Run Standalone Zoom Agent

```bash
cd d:\AIProjects\VoiceAIAgent
python src/zoom_dialer.py dev
```

Then dispatch the agent to dial a specific meeting:

```bash
lk dispatch create \
    --new-room \
    --agent-name zoom-dialing-agent \
    --metadata '{"meeting_id": "1234567890", "meeting_password": "password123"}'
```

### Option B: Use Python to Dispatch

Create `scripts/dial_zoom.py`:

```python
"""Script to dispatch agent to join a Zoom meeting."""

import asyncio
from livekit import api

async def main():
    lkapi = api.LiveKitAPI()
    
    # Meeting details
    meeting_id = "1234567890"
    meeting_password = ""  # Leave empty if no password
    
    # Dispatch agent
    dispatch = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name="zoom-dialing-agent",
            room=f"zoom-meeting-{meeting_id}",
            metadata=f'{{"meeting_id": "{meeting_id}", "meeting_password": "{meeting_password}"}}'
        )
    )
    
    print(f"Agent dispatched: {dispatch}")
    await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
```

Run with:
```bash
python scripts/dial_zoom.py
```

---

## Part 5: Testing

### 5.1 Start a Zoom Meeting

1. Open Zoom and start a meeting
2. Get the Meeting ID (e.g., `123 456 7890`)
3. Note the password if set

### 5.2 Dispatch the Agent

Using the dispatch commands above, send your agent to the meeting.

### 5.3 Verify Join

In Zoom, you should see:
- A participant named "AI Agent" (or your configured caller ID)
- The participant shows as "Phone" type
- Audio from the agent plays through the meeting

### 5.4 Test Conversation

Speak to the agent - it should respond via audio in the Zoom meeting.

---

## Part 6: Troubleshooting

### Issue: SIP 404 Not Found
**Cause**: Wrong Zoom SIP URI format
**Solution**: Verify format is `meeting-id@zoomcrc.com`

### Issue: SIP 403 Forbidden
**Cause**: Authentication failure with Twilio
**Solution**: 
- Check username/password in LiveKit trunk config
- Verify IP Access Control List includes LiveKit IPs

### Issue: SIP 486 Busy or 603 Declined
**Cause**: Zoom meeting not accepting SIP calls
**Solution**:
- Ensure meeting is started
- Check if meeting requires password (include in URI)
- Verify Zoom account has H.323/SIP Room Connector enabled

### Issue: Agent connects but no audio
**Cause**: Codec mismatch or media issue
**Solution**:
- Check LiveKit logs for RTP errors
- Ensure firewall allows RTP traffic (UDP 10000-20000)
- Verify Twilio trunk codecs include G.711 (μ-law and A-law)

### Issue: Call times out
**Cause**: Network or routing issue
**Solution**:
- Check Twilio trunk status
- Verify Zoom SIP domain `zoomcrc.com` is reachable
- Check LiveKit SIP logs for INVITE/RESPONSE messages

---

## Zoom SIP Reference

### SIP URI Formats

| Scenario | Format |
|----------|--------|
| No password | `meeting-id@zoomcrc.com` |
| With password | `meeting-id.password@zoomcrc.com` |
| With extension | `meeting-id.ext@zoomcrc.com` |

### Zoom SIP Domains

| Region | Domain |
|--------|--------|
| Global/Default | `zoomcrc.com` |
| US | `sip.zoomcrc.com` |

### DTMF Support

To send DTMF tones (e.g., for meeting controls), use the `dtmf` parameter:

```python
await ctx.api.sip.create_sip_participant(
    api.CreateSIPParticipantRequest(
        # ... other params ...
        dtmf="9",  # Press 9 to raise hand, etc.
    )
)
```

---

## Security Considerations

1. **Protect SIP Credentials**: Store Twilio SIP credentials in environment variables, never commit to git
2. **Restrict Trunk Usage**: Limit outbound trunk to specific IP ranges if possible
3. **Meeting Passwords**: Always include passwords when connecting to protected meetings
4. **Audit Logs**: Enable logging to track all Zoom connections
5. **Rate Limiting**: Implement rate limiting to prevent abuse

---

## Cost Considerations

- **Twilio**: Charges for SIP trunking and PSTN minutes
- **Zoom**: H.323/SIP Room Connector may require paid plan
- **LiveKit**: Standard egress charges apply

Check current pricing:
- [Twilio Elastic SIP Trunking Pricing](https://www.twilio.com/sip-trunking/pricing)
- [Zoom Room Connector Pricing](https://zoom.us/pricing)

---

## Next Steps

1. Set up Twilio Elastic SIP Trunk (Part 1)
2. Configure LiveKit outbound trunk (Part 2)
3. Deploy the Zoom agent code (Part 3)
4. Test with a private Zoom meeting (Part 5)
5. Share demo link with client

For questions or issues, refer to:
- [LiveKit Telephony Docs](https://docs.livekit.io/telephony/)
- [Twilio Elastic SIP Docs](https://www.twilio.com/docs/sip-trunking)
- [Zoom H.323/SIP Guide](https://support.zoom.us/hc/en-us/articles/201362663-H-323-SIP-Room-Connector)


## Files Created/Modified

### 1. **Documentation** - `DeveloperDocs/zoom.md`
Complete guide covering:
- Architecture overview with SIP flow diagram
- Twilio Elastic SIP Trunk setup (Part 1)
- LiveKit outbound trunk configuration (Part 2)
- Agent code modifications (Part 3)
- Running and testing instructions (Parts 4-6)
- Troubleshooting guide for common SIP errors

### 2. **Zoom Dialer Agent** - `src/zoom_dialer.py`
A standalone agent that:
- Dials into Zoom meetings via SIP
- Uses Zoom's SIP URI format: `meeting-id@zoomcrc.com`
- Handles meeting passwords
- Configurable caller ID name
- Proper error handling for SIP responses

### 3. **Dispatch Script** - `scripts/dial_zoom.py`
CLI tool to dispatch the agent to Zoom meetings:
```bash
python scripts/dial_zoom.py --meeting-id 1234567890 --password secret123
```

### 4. **Environment Variables** - `.env.local` updated
Added Zoom-specific configuration:
```env
ZOOM_SIP_TRUNK_ID=ST_xxxxx
ZOOM_MEETING_ID=
ZOOM_MEETING_PASSWORD=
ZOOM_CALLER_ID_NAME=AI Agent
```

### 5. **LiveKit Trunk Config** - `outbound-trunk-zoom.json`
Template for creating the outbound SIP trunk:
```bash
lk sip outbound create outbound-trunk-zoom.json
```

### 6. **Enhanced Call Attending Agent** - `src/call_attending_agent.py`
Added `dial_zoom_meeting()` function for optional Zoom integration in your existing agent.

## Quick Start Steps

1. **Set up Twilio Elastic SIP Trunk** (follow `zoom.md` Part 1)
   - Create trunk named "LiveKit-Zoom-Outbound"
   - Configure origination and termination
   - Set up IP Access Control List and credentials

2. **Create LiveKit Outbound Trunk**
   ```bash
   # Edit outbound-trunk-zoom.json with your Twilio credentials
   lk sip outbound create outbound-trunk-zoom.json
   # Save the returned ST_xxxxx ID
   ```

3. **Update Environment**
   ```bash
   # Add to .env.local
   ZOOM_SIP_TRUNK_ID=ST_xxxxx  # From step 2
   ```

4. **Run the Agent**
   ```bash
   python src/zoom_dialer.py dev
   ```

5. **Dispatch to Zoom Meeting**
   ```bash
   python scripts/dial_zoom.py --meeting-id YOUR_MEETING_ID
   ```

The agent will appear as "AI Agent" (phone participant) in your Zoom meeting.