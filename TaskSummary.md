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


## Plan for HuggingFace
Based on my research of the LiveKit Agents SDK, I found there are **three main approaches** to use HuggingFace models instead of Deepgram/OpenAI/Cartesia. Here's a detailed plan for your `src/agent.py` code changes:

---

## Option 1: HuggingFace Inference API (Easiest - No Custom Plugin)

Use HuggingFace's OpenAI-compatible Serverless API or TGI endpoints.

**Required `.env.local` changes:**
```bash
HF_API_KEY=hf_xxx
HF_LLM_MODEL=microsoft/DialoGPT-medium  # or meta-llama/Llama-3-8B-Instruct, etc.
HF_STT_MODEL=SuyKam/whisper-small-espanol  # or any Whisper model on HF
HF_TTS_MODEL=microsoft/speecht5_tts  # or any TTS model
```

**Code changes for `src/agent.py`:**

1. Replace imports:
```python
# Remove:
from livekit.plugins import openai, deepgram, cartesia

# Add:
from livekit.plugins import openai
# Or use requests/aiohttp directly for models not OpenAI-compatible
```

2. Replace STT with HuggingFace Whisper API:
```python
# Instead of:
stt=deepgram.STT(model="nova-3", language="multi")

# Use OpenAI-compatible wrapper pointing to HuggingFace:
stt=openai.STT(
    model="SuyKam/whisper-small-espanol",  # or any HF Whisper model
    api_key=os.getenv("HF_API_KEY"),
    base_url="https://api-inference.huggingface.co/v1",  # Serverless API
    # OR for dedicated inference endpoint:
    # base_url="https://your-endpoint.huggingface.cloud/v1",
)
```

3. Replace LLM with HuggingFace model:
```python
# Instead of:
llm=openai.responses.LLM(model="gpt-4.1-mini"),

# Use:
llm=openai.LLM(
    model="microsoft/DialoGPT-medium",  # or meta-llama/Llama-3-8B-Instruct
    api_key=os.getenv("HF_API_KEY"),
    base_url="https://api-inference.huggingface.co/v1",
)
```

4. Replace TTS with HuggingFace TTS:
```python
# Instead of:
tts=cartesia.TTS(model="sonic-3", voice="..."),

# Use a HuggingFace TTS endpoint via HTTP calls in a custom TTS class
# (see Option 2 for custom implementation, or use existing HF TTS SDK)
```

---

## Option 2: Local Transformers Models (Full Control, No API Calls)

Run models locally using `transformers`, `torch`, `onnxruntime`, etc.

**Required package installation:**
```bash
pip install transformers torch accelerate onnxruntime huggingface_hub
pip install TTS  # For coqui TTS or similar
pip install faster-whisper  # For local Whisper
```

**Code changes for `src/agent.py`:**

1. Add imports and create wrapper classes:
```python
from livekit.agents import llm, stt, tts
from livekit.agents.llm import LLM, ChatMessage
from typing import AsyncIterator
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from faster_whisper import WhisperModel
from TTS.api import TTS as CoquiTTS

# Custom local LLM implementation
class HuggingFaceLLM(LLM):
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        super().__init__()
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load model once at initialization
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
        )
        
    async def chat(self, chat_ctx, fnc_ctx=None, temperature=0.8) -> AsyncIterator[llm.ChatChunk]:
        # Convert LiveKit chat context to HF format
        messages = self._convert_chat_context(chat_ctx)
        
        # Tokenize and generate
        inputs = self.tokenizer.apply_chat_template(
            messages, 
            return_tensors="pt",
            return_dict=True
        ).to(self.device)
        
        # Stream the output
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Yield as ChatChunk
        yield llm.ChatChunk(
            delta=llm.ChoiceDelta(content=generated_text, role="assistant")
        )

# Custom local STT implementation  
class HuggingFaceSTT(stt.STT):
    def __init__(self, model_size: str = "base"):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False,
            )
        )
        # Load Whisper model locally
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
    async def recognize(self, buffer, language="en"):
        # Convert audio buffer and transcribe
        segments, info = self.model.transcribe(buffer, language=language)
        text = " ".join([segment.text for segment in segments])
        
        # Return speech event
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=text, language=language)]
        )

# Custom local TTS implementation
class HuggingFaceTTS(tts.TTS):
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=22050,
        )
        # Load local TTS model
        self.tts = CoquiTTS(model_name)
        
    async def synthesize(self, text: str):
        # Generate audio
        wav = self.tts.tts(text=text)
        
        # Return audio emitter with generated audio
        # (implementation details for audio streaming)
        return self._create_audio_stream(wav)
```

2. Update AgentSession:
```python
session = AgentSession(
    stt=HuggingFaceSTT(model_size="base"),
    llm=HuggingFaceLLM(model_name="microsoft/DialoGPT-medium"),
    tts=HuggingFaceTTS(model_name="tts_models/en/ljspeech/tacotron2-DDC"),
    vad=silero.VAD.load(),
)
```

---

## Option 3: LiteLLM Gateway (Drop-in Compatibility)

Use LiteLLM as an OpenAI-compatible proxy for HuggingFace models.

**Setup:**
```bash
pip install litellm
# Run gateway: litellm --model huggingface/mistralai/Mistral-7B-Instruct-v0.1
```

**Code changes for `src/agent.py`:**

1. Update imports:
```python
from livekit.plugins import openai
```

2. Update AgentSession to use LiteLLM proxy:
```python
session = AgentSession(
    stt=openai.STT(
        model="whisper-1",
        api_key="not-needed",
        base_url="http://localhost:4000",  # LiteLLM proxy
    ),
    llm=openai.LLM(
        model="huggingface/mistralai/Mistral-7B-Instruct-v0.1",
        api_key="not-needed",
        base_url="http://localhost:4000",
    ),
    tts=openai.TTS(
        model="tts-1",
        api_key="not-needed", 
        base_url="http://localhost:4000",
    ),
    vad=silero.VAD.load(),
)
```

---

## Recommendation

| Approach | Latency | Complexity | Cost | Best For |
|----------|---------|------------|------|----------|
| **Option 1: HF Inference API** | Higher (network) | Low | Pay-per-use | Quick prototyping, no GPU |
| **Option 2: Local Models** | Low (local) | High | Free (own hardware) | Privacy, high volume, have GPU |
| **Option 3: LiteLLM** | Medium | Low | Proxy costs | Multiple model providers |

**For your use case (casual phone conversations):**
- Start with **Option 1** for quickest implementation
- **Option 2** if you need data privacy and have GPU resources
- **Option 3** if you want flexibility to switch between providers
