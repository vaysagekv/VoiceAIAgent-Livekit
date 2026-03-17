# Voice AI CLI 🤖📞

A Python CLI application that uses LiveKit Agents to make outbound phone calls and have casual AI-powered conversations with the callee.

## Features

- 🔊 **Voice AI Agent**: Natural-sounding conversation using Deepgram STT, OpenAI LLM, and Cartesia TTS
- 📱 **Outbound Calling**: Make real phone calls via SIP trunk integration
- 🤝 **Casual Conversation**: Friendly, engaging AI that can chat about various topics
- 🛠️ **CLI Interface**: Simple command-line interface to initiate calls
- 💻 **WebRTC Testing**: Test without phone calls via LiveKit Playground

## Architecture

```
Voice AI Caller
├── STT: Deepgram Nova-3 (real-time transcription)
├── LLM: OpenAI GPT-4.1 mini (conversation intelligence)
├── TTS: Cartesia Sonic-3 (natural speech synthesis)
├── VAD: Silero (voice activity detection)
└── Turn Detection: Multilingual model (natural turn-taking)
```

## Prerequisites

1. **LiveKit Cloud Account** (free)
   - Sign up at [cloud.livekit.io](https://cloud.livekit.io)
   - Create a project and copy credentials

2. **SIP Provider** (for phone calls)
   - Recommended: [Twilio](https://www.twilio.com), [Telnyx](https://telnyx.com), or [Plivo](https://www.plivo.com)
   - Create an outbound SIP trunk
   - Get your trunk ID

3. **Python 3.10+** and `uv` package manager

## Installation

**1. Install UV (if not already installed):**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Clone and setup project:**
```bash
# Navigate to project directory
cd voice-ai-cli

# Create virtual environment and install dependencies
uv sync

# Download required model files
uv run src/agent.py download-files
```

**3. Configure environment:**
```bash
# Copy template and edit
cp .env.local .env.local.backup
# Edit .env.local with your credentials
```

Update `.env.local` with your LiveKit credentials:
```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

SIP_OUTBOUND_TRUNK_ID=ST_xxxxx  # From your SIP provider setup
CALLER_DISPLAY_NAME=AI Assistant  # What appears as caller ID
```

## Usage

### Check Configuration
```bash
# Verify your setup is complete
uv run src/cli.py configure
```

### Validate Phone Number
```bash
# Test phone number formatting
uv run src/cli.py validate +15551234567
```

### Make a Call
```bash
# Basic call
uv run src/cli.py call +15551234567

# With custom display name
uv run src/cli.py call +15551234567 --room-name "my-call-room"

# Wait for call to complete (blocking)
uv run src/cli.py call +15551234567 --wait
```

### Run Agent in Development Mode
```bash
# Start agent server for testing via LiveKit Playground
uv run src/agent.py dev
```

Then connect via [LiveKit Playground](https://agents.livekit.io) to test without making phone calls.

## Project Structure

```
voice-ai-cli/
├── pyproject.toml           # Project dependencies
├── .env.local               # Environment variables
├── src/
│   ├── __init__.py
│   ├── agent.py             # Voice AI agent implementation
│   ├── call_manager.py      # Outbound calling logic
│   └── cli.py               # Command-line interface
└── tests/
    ├── __init__.py
    └── test_agent.py        # Test suite
```

## How It Works

1. **CLI receives phone number** from user input
2. **CallManager creates an agent dispatch** to a new room
3. **Agent starts and creates a SIP participant** to dial the phone number
4. **SIP provider connects the call** to the actual phone
5. **Voice AI agent engages** in conversation when callee answers
6. **Natural conversation flow** with turn detection and interruptions
7. **Call ends** when user says goodbye or agent detects conversation end

## Testing

Run the test suite:
```bash
# Run all tests
uv run pytest tests/

# Run with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_agent.py -v
```

## Development Mode

Test without making real phone calls:

```bash
# Start agent in dev mode
uv run src/agent.py dev
```

The agent will be available in the LiveKit Playground where you can chat via browser instead of phone.

## Troubleshooting

### Missing Credentials
If you see "Missing LiveKit credentials", check that:
- `.env.local` file exists in project root
- All required variables are set (not placeholder values)

### SIP Trunk Errors
If call fails to initiate:
- Verify `SIP_OUTBOUND_TRUNK_ID` is set correctly
- Check your SIP trunk configuration in LiveKit Cloud dashboard
- Ensure your SIP provider account has sufficient balance

### Model Downloads
If starting agent fails:
```bash
# Re-download model files
uv run src/agent.py download-files
```

## Advanced Configuration

### Custom Agent Instructions

Edit `src/agent.py` to modify the agent's personality:

```python
class CasualConversationAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""Your custom instructions here...""",
        )
```

### Using Different AI Models

The agent uses LiveKit Inference by default. To use your own API keys:

1. Install the respective plugin:
   ```bash
   uv add livekit-plugins-openai
   ```

2. Pass API key to AgentSession:
   ```python
   session = AgentSession(
       llm=openai.LLM(api_key="your-key", model="gpt-4"),
       # ... other config
   )
   ```

## Resources

- [LiveKit Agents Documentation](https://docs.livekit.io/agents)
- [LiveKit Telephony Guide](https://docs.livekit.io/telephony)
- [SIP Trunk Setup](https://docs.livekit.io/telephony/start/sip-trunk-setup)
- [Voice AI Quickstart](https://docs.livekit.io/agents/start/voice-ai)

## License

MIT