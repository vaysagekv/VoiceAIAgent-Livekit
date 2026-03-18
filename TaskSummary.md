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

## Local Inference

## Files Modified

### 1. `src/agent.py`
**Changes:**
- **Replaced imports:** Added `from livekit.plugins import openai, deepgram, cartesia`
- **Removed:** `MultilingualModel` import (this is a proprietary LiveKit Cloud model)
- **Updated Session Configuration:**
  - **STT:** Changed from string descriptor `"deepgram/nova-3:multi"` to direct plugin: `deepgram.STT(model="nova-3", language="multi")`
  - **LLM:** Changed from string descriptor `"openai/gpt-4.1-mini"` to direct plugin: `openai.responses.LLM(model="gpt-4.1-mini")`
  - **TTS:** Changed from string descriptor `"cartesia/sonic-3:..."` to direct plugin: `cartesia.TTS(model="sonic-3", voice="...")`
  - **Turn Detection:** Removed `MultilingualModel()` - using VAD-based turn detection instead (built-in when not specified)

### 2. `.env.local`
**Added Direct Provider API Keys:**
```bash
OPENAI_API_KEY=your-openai-api-key-here
DEEPGRAM_API_KEY=your-deepgram-api-key-here
CARTESIA_API_KEY=your-cartesia-api-key-here
```

## What's Different

| Component | Before (LiveKit Inference) | After (Your Own Keys) |
|-----------|------------------------------|------------------------|
| **STT** | LiveKit Cloud routes to Deepgram | Direct Deepgram API connection |
| **LLM** | LiveKit Cloud routes to OpenAI | Direct OpenAI API connection |
| **TTS** | LiveKit Cloud routes to Cartesia | Direct Cartesia API connection |
| **Turn Detection** | AI-powered MultilingualModel | VAD-based detection |

## Important Notes

1. **Get Your API Keys:**
   - OpenAI: https://platform.openai.com/api-keys
   - Deepgram: https://console.deepgram.com/
   - Cartesia: https://play.cartesia.ai/keys

2. **MultilingualModel Removed:** This was the only component requiring LiveKit Cloud Inference. It's a proprietary AI model for context-aware turn detection. The agent now uses VAD-based detection which is less sophisticated but fully self-hosted.

3. **LiveKit Server:** You're still using LiveKit Cloud for the WebRTC/media transport (`LIVEKIT_URL`). To be 100% independent, deploy your own LiveKit server (see https://docs.livekit.io/transport/self-hosting/).

4. **Dependencies:** Your `pyproject.toml` already has the required plugins: `livekit-plugins-openai`, `livekit-plugins-deepgram`, `livekit-plugins-cartesia`.

5. **Costs:** You'll now manage billing directly with OpenAI, Deepgram, and Cartesia instead of through LiveKit Cloud.