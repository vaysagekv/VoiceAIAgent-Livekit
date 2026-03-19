# Call Attending Agent Documentation

## Overview

The **Call Attending Agent** is an AI-powered voice agent built with LiveKit that handles inbound phone calls after business hours. When a call comes in after the configured time threshold (default: 5 PM), the agent answers with a greeting, records the caller's requirements, and saves the call details to JSON files.

## Features

- 🕐 **Time-Based Call Filtering**: Only attends calls after configurable business hours
- 🎙️ **Voice AI**: Natural conversation using Groq STT/LLM and Cartesia TTS
- 📝 **Call Logging**: Automatically records call details (phone number, time, summary, transcript) to JSON
- 🔧 **Configurable**: Adjustable time threshold, agent name, and logging options
- 📞 **Inbound Call Handling**: Designed for SIP trunk inbound call scenarios
- 🎯 **Graceful Termination**: Uses LiveKit's EndCallTool for professional call ending

---

## Prerequisites

### 1. LiveKit Cloud Account

- Sign up at [https://cloud.livekit.io](https://cloud.livekit.io)
- Create a new project
- Copy your credentials (URL, API Key, API Secret)

### 2. SIP Trunk Configuration

To receive inbound calls, you need a SIP trunk:

**Option A: LiveKit Phone Numbers**
- Purchase a phone number directly in LiveKit Cloud
- Go to **Telephony → Phone Numbers → Buy number**

**Option B: External SIP Provider** (Twilio, Telnyx, Plivo, etc.)
- Configure an inbound SIP trunk
- Follow provider-specific setup guides at [LiveKit Telephony Docs](https://docs.livekit.io/telephony)

### 3. Python Environment

- Python 3.10 or higher
- `uv` package manager installed

### 4. AI Provider API Keys

- **Groq API Key**: For speech-to-text and LLM
  - Get from: https://console.groq.com/keys
- **Cartesia API Key**: For text-to-speech
  - Get from: https://play.cartesia.ai/keys

---

## Environment Variables

Create or update your `.env.local` file with the following variables:

### Required Variables

```env
# LiveKit Server Credentials
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Groq API (STT and LLM)
GROQ_API_KEY=gsk_your-groq-api-key

# Cartesia API (TTS)
CARTESIA_API_KEY=sk_car_your-cartesia-key
```

### Optional Variables

```env
# SIP Trunk ID (if using outbound calling from other agents)
SIP_OUTBOUND_TRUNK_ID=ST_xxxxx

# Groq Model Configuration (optional overrides)
GROQ_LLM_MODEL=llama-3.3-70b-versatile    # Default: llama-3.3-70b-versatile
GROQ_STT_MODEL=whisper-large-v3-turbo     # Default: whisper-large-v3-turbo

# Cartesia TTS Configuration (optional overrides)
CARTESIA_TTS_MODEL=sonic-3                # Default: sonic-3
CARTESIA_TTS_VOICE=9626c31c-bec5-4cca-baa8-f8ba9e84c8bc  # Default: Jacqueline voice

# Call Attending Agent Configuration
CALL_ATTEND_AFTER_HOUR=17                 # Time threshold (24h format, default: 17 = 5 PM)
CALL_ATTEND_AGENT_NAME=Tina               # Agent name used in greeting (default: Tina)
CALL_ATTEND_ENABLE_LOGGING=true           # Enable JSON call logging (default: true)
CALL_ATTEND_LOGS_DIR=calllogs             # Directory for call logs (default: calllogs)
```

---

## Installation & Setup

### 1. Clone and Setup

```bash
# Navigate to project directory
cd voice-ai-cli

# Install dependencies
uv sync
```

### 2. Configure Environment

```bash
# Copy environment file
cp .env.local .env.local.backup

# Edit .env.local with your credentials
# Add all required variables listed above
```

### 3. Verify Configuration

```bash
# Check CLI configuration
uv run src/cli.py configure
```

---

## Deployment

### Step 1: Create Dispatch Rule

You need to create a dispatch rule in LiveKit Cloud to route inbound calls to this agent.

**Via LiveKit Cloud Dashboard:**

1. Sign in to [https://cloud.livekit.io](https://cloud.livekit.io)
2. Select **Telephony → Dispatch rules**
3. Click **Create new dispatch rule**
4. Select **JSON editor** tab
5. Paste the following JSON:

```json
{
  "rule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "inbound-call-"
    }
  },
  "name": "Call Attending Agent Dispatch",
  "roomConfig": {
    "agents": [{
      "agentName": "call-attending-agent",
      "metadata": ""
    }]
  }
}
```

6. Click **Create**

**Via LiveKit CLI:**

Create a file `dispatch-rule.json`:

```json
{
  "dispatch_rule": {
    "rule": {
      "dispatchRuleIndividual": {
        "roomPrefix": "inbound-call-"
      }
    },
    "name": "Call Attending Agent Dispatch",
    "roomConfig": {
      "agents": [{
        "agentName": "call-attending-agent",
        "metadata": ""
      }]
    }
  }
}
```

Then run:

```bash
lk sip dispatch create dispatch-rule.json
```

### Step 2: Start the Agent

**Development Mode (for testing):**

```bash
uv run src/call_attending_agent.py dev
```

This connects to LiveKit Cloud and waits for incoming calls.

**Production Deployment:**

Deploy to LiveKit Cloud:

```bash
# Deploy using LiveKit CLI
lk agent deploy src/call_attending_agent.py
```

Or run on your own infrastructure:

```bash
uv run src/call_attending_agent.py start
```

### Step 3: Test the Agent

Once the agent is running and the dispatch rule is configured:

1. Call your LiveKit phone number
2. If calling after 5 PM (or your configured threshold):
   - Agent answers: *"I am AI agent Tina talking. Please tell your requirement. I will record it."*
   - Have a conversation
   - Agent records the call details
3. If calling before 5 PM:
   - Agent declines: *"Thank you for calling. Our office is currently open. Please call back during business hours before 17:00. Goodbye."*

---

## Call Log Format

After each call, a JSON file is created in the `calllogs/` directory:

**Filename format:** `call_log_<timestamp>_<room_name>.json`

**Example:**

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "room_name": "inbound-call-+15551234567-a1b2c3d4",
  "phone_number": "+15551234567",
  "start_time": "2026-03-19T17:30:00.123456",
  "end_time": "2026-03-19T17:35:30.654321",
  "duration_seconds": 330,
  "agent_name": "Tina",
  "call_summary": "Call recorded with 8 messages. Main topic: user: I need help with my order",
  "full_transcript": [
    {
      "role": "assistant",
      "content": "I am AI agent Tina talking. Please tell your requirement. I will record it.",
      "timestamp": "2026-03-19T17:30:05.123456"
    },
    {
      "role": "user",
      "content": "I need help with my order",
      "timestamp": "2026-03-19T17:30:12.234567"
    }
  ],
  "status": "completed",
  "call_attend_threshold_hour": 17
}
```

**Statuses:**
- `completed`: Normal call completion
- `rejected_after_hours`: Call received before threshold time

---

## Configuration Examples

### Change Time Threshold to 6 PM

```env
CALL_ATTEND_AFTER_HOUR=18
```

### Change Agent Name

```env
CALL_ATTEND_AGENT_NAME=Sarah
```

Greeting becomes: *"I am AI agent Sarah talking. Please tell your requirement. I will record it."*

### Disable Call Logging

```env
CALL_ATTEND_ENABLE_LOGGING=false
```

### Custom Logs Directory

```env
CALL_ATTEND_LOGS_DIR=/var/log/call-logs
```

---

## Troubleshooting

### Agent Not Receiving Calls

1. **Check dispatch rule**: Ensure dispatch rule is created with correct `agentName`
2. **Verify SIP trunk**: Confirm inbound trunk is properly configured
3. **Check agent is running**: Run `uv run src/call_attending_agent.py dev` and verify connection

### No Call Logs Created

1. **Check configuration**: Verify `CALL_ATTEND_ENABLE_LOGGING=true`
2. **Check permissions**: Ensure write access to `calllogs/` directory
3. **Check session end**: Logs are created when session ends (caller hangs up or agent ends call)

### Agent Not Answering After Hours

1. **Check system time**: Verify server time matches expected timezone
2. **Check configuration**: Verify `CALL_ATTEND_AFTER_HOUR` is set correctly
3. **Test time check**: Add logging to verify `is_after_hours()` function

### Audio Quality Issues

1. **Check noise cancellation**: Ensure BVC is working (configured in agent)
2. **Check VAD settings**: Verify Silero VAD is loaded correctly
3. **Check STT/TTS models**: Verify Groq and Cartesia API keys are valid

---

## Testing

Run the test suite:

```bash
# Run all tests
uv run pytest tests/test_call_attending_agent.py -v

# Run specific test class
uv run pytest tests/test_call_attending_agent.py::TestCallAttendingAgent -v

# Run time-based tests
uv run pytest tests/test_call_attending_agent.py::TestTimeBasedCallAcceptance -v
```

---

## Architecture

```
Inbound Call Flow:
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Phone Caller   │────▶│  LiveKit SIP │────▶│  Dispatch Rule  │
└─────────────────┘     └──────────────┘     └─────────────────┘
                                                       │
                              ┌──────────────────────┘
                              ▼
                       ┌──────────────┐
                       │ CallAttending│
                       │    Agent     │
                       └──────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Time     │    │ Greeting │    │ EndCall  │
        │ Check    │    │ & Record │    │   Tool   │
        └──────────┘    └──────────┘    └──────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │  Call Log    │
                       │  JSON File   │
                       └──────────────┘
```

---

## API Reference

### CallAttendingAgent Class

Extends `livekit.agents.Agent`

**Methods:**
- `on_enter()`: Generates greeting when agent starts

### Helper Functions

- `get_caller_phone_number(ctx)`: Extracts phone number from SIP participant
- `is_after_hours()`: Checks if current time >= threshold
- `save_call_log(...)`: Saves call details to JSON file
- `generate_call_summary(session)`: Generates summary from conversation history
- `handle_session_end(ctx)`: Callback for session cleanup and logging

---

## Resources

- [LiveKit Agents Documentation](https://docs.livekit.io/agents)
- [LiveKit Telephony Guide](https://docs.livekit.io/telephony)
- [SIP Trunk Setup](https://docs.livekit.io/telephony/start/sip-trunk-setup)
- [Groq Console](https://console.groq.com/keys)
- [Cartesia Voices](https://play.cartesia.ai/voices)

---

## License

MIT License - See LICENSE file for details