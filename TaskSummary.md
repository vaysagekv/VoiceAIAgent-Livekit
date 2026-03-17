## Project Structure

```
VoiceAIAgent/
├── pyproject.toml          # Project configuration with all dependencies
├── .env.local              # Environment variables template
├── .gitignore              # Git ignore file
├── README.md               # Comprehensive documentation
├── src/
│   ├── __init__.py
│   ├── agent.py            # Voice AI agent implementation
│   ├── call_manager.py     # Outbound calling logic
│   └── cli.py              # Command-line interface
└── tests/
    ├── __init__.py
    └── test_agent.py       # Complete test suite (15 tests - all passing)
```

## Key Features

### 1. Voice AI Agent (`src/agent.py`)
- **Agent Name**: `casual-caller`
- **Personality**: Friendly, engaging conversationalist
- **Voice Pipeline**:
  - STT: Deepgram Nova-3 (real-time transcription)
  - LLM: OpenAI GPT-4.1 mini (via LiveKit Inference)
  - TTS: Cartesia Sonic-3 (natural speech synthesis)
  - VAD: Silero (voice activity detection)
  - Turn Detection: Multilingual model (natural turn-taking)
- **Tools**: `end_call` function tool for graceful call termination
- **Telephony Optimized**: Noise cancellation for SIP calls

### 2. Call Management (`src/call_manager.py`)
- `CallManager` class for outbound calling
- Phone number normalization (E.164 format)
- Phone number validation
- Agent dispatch creation via LiveKit API
- SIP participant creation for actual phone calls

### 3. CLI Interface (`src/cli.py`)
Commands:
- `voice-ai call <number>` - Make outbound calls
- `voice-ai configure` - Check configuration status
- `voice-ai validate <number>` - Validate phone number format

### 4. Tests (`tests/test_agent.py`)
15 comprehensive tests covering:
- Agent initialization and instructions
- Tool availability (end_call)
- Phone number validation (US and international)
- Call manager credential handling
- Phone number normalization

All tests pass ✅

## How to Use

### 1. Install Dependencies
```bash
cd d:\AIProjects\VoiceAIAgent
uv sync
uv run src/agent.py download-files
```

### 2. Configure Credentials
Edit `.env.local`:
```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
SIP_OUTBOUND_TRUNK_ID=ST_xxxxx
CALLER_DISPLAY_NAME=AI Assistant
```

### 3. Check Configuration
```bash
uv run src/cli.py configure
```

### 4. Make a Call
```bash
# Validate phone number first
uv run src/cli.py validate +15551234567

# Make the call
uv run src/cli.py call +15551234567
```

### 5. Test Without Phone (Dev Mode)
```bash
uv run src/agent.py dev
```
Then connect via [LiveKit Playground](https://agents.livekit.io) to test via browser.

## Prerequisites to Run

1. **LiveKit Cloud Account**: Sign up at [cloud.livekit.io](https://cloud.livekit.io)
2. **SIP Provider**: Set up outbound SIP trunk (Twilio, Telnyx, etc.)
   - Get trunk ID from LiveKit Cloud dashboard after configuration
3. **Python 3.10+** with `uv` package manager

## Architecture Flow

1. CLI receives phone number → CallManager validates
2. CallManager creates agent dispatch to new room
3. Voice AI agent starts and creates SIP participant
4. SIP provider dials the phone number
5. When answered, AI engages in natural conversation
6. Call ends via end_call tool or user hangs up

The implementation follows LiveKit best practices including proper testing, telephony optimization, and voice-optimized agent instructions.