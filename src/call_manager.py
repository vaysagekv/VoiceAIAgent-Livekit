"""Call management utilities for outbound phone calls."""

import asyncio
import json
import os
from typing import Optional

from dotenv import load_dotenv
from livekit import api

load_dotenv(".env.local")


class CallManager:
    """Manages outbound phone calls via LiveKit SIP."""

    def __init__(
        self,
        livekit_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sip_trunk_id: Optional[str] = None,
    ):
        """Initialize the call manager with LiveKit credentials.
        
        Args:
            livekit_url: LiveKit Cloud URL (defaults to env var)
            api_key: LiveKit API key (defaults to env var)
            api_secret: LiveKit API secret (defaults to env var)
            sip_trunk_id: SIP outbound trunk ID (defaults to env var)
        """
        self.livekit_url = livekit_url if livekit_url is not None else os.getenv("LIVEKIT_URL")
        self.api_key = api_key if api_key is not None else os.getenv("LIVEKIT_API_KEY")
        self.api_secret = api_secret if api_secret is not None else os.getenv("LIVEKIT_API_SECRET")
        self.sip_trunk_id = sip_trunk_id if sip_trunk_id is not None else os.getenv("SIP_OUTBOUND_TRUNK_ID")
        self.caller_display_name = os.getenv("CALLER_DISPLAY_NAME", "AI Assistant")
        
        # Validate credentials are present and not placeholders
        def is_valid(value: Optional[str]) -> bool:
            if not value:
                return False
            # Check for common placeholder patterns
            placeholders = ["your-", "xxxx", "xxxxx", "placeholder"]
            return not any(p in value.lower() for p in placeholders)
        
        if not all(is_valid(v) for v in [self.livekit_url, self.api_key, self.api_secret]):
            raise ValueError(
                "Missing LiveKit credentials. "
                "Set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in .env.local"
            )

    async def initiate_call(
        self,
        phone_number: str,
        room_name: Optional[str] = None,
        agent_name: str = "casual-caller",
        metadata: Optional[dict] = None,
    ) -> dict:
        """Initiate an outbound phone call.
        
        This method:
        1. Creates a dispatch for the voice AI agent
        2. The agent then creates the SIP participant to dial the number
        
        Args:
            phone_number: The phone number to call (e.g., "+15551234567")
            room_name: Optional room name (auto-generated if not provided)
            agent_name: The agent to dispatch (default: casual-caller)
            metadata: Additional metadata to pass to the agent
            
        Returns:
            Dict with room_name and dispatch info
        """
        if not self.sip_trunk_id:
            raise ValueError(
                "SIP_OUTBOUND_TRUNK_ID not set. "
                "Configure a SIP trunk first via LiveKit Cloud."
            )
        
        # Normalize phone number
        phone_number = self._normalize_phone_number(phone_number)
        
        # Generate room name if not provided
        if not room_name:
            import uuid
            room_name = f"call-{uuid.uuid4().hex[:8]}"
        
        # Build metadata with phone number
        call_metadata = {"phone_number": phone_number}
        if metadata:
            call_metadata.update(metadata)
        
        # Create LiveKit API client
        lkapi = api.LiveKitAPI(
            url=self.livekit_url,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )
        
        try:
            # Create agent dispatch
            # This will start the agent, which will then create the SIP participant
            dispatch = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=agent_name,
                    room=room_name,
                    metadata=json.dumps(call_metadata),
                )
            )
            
            return {
                "room_name": room_name,
                "phone_number": phone_number,
                "dispatch_id": dispatch.id,
                "agent_name": agent_name,
                "status": "initiated",
            }
            
        finally:
            await lkapi.aclose()

    def _normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number to E.164 format.
        
        Args:
            phone_number: Raw phone number string
            
        Returns:
            Normalized phone number with + prefix
        """
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # Ensure it starts with +
        if not cleaned.startswith('+'):
            # Assume US number if no country code
            cleaned = '+1' + cleaned.lstrip('1')
            
        return cleaned

    def validate_phone_number(self, phone_number: str) -> bool:
        """Validate a phone number format.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            normalized = self._normalize_phone_number(phone_number)
            # E.164 format: + followed by 7-15 digits
            return (
                normalized.startswith('+') and
                len(normalized) >= 8 and
                len(normalized) <= 16 and
                normalized[1:].isdigit()
            )
        except Exception:
            return False


async def make_call(
    phone_number: str,
    room_name: Optional[str] = None,
    agent_name: str = "casual-caller",
) -> dict:
    """Convenience function to make a single outbound call.
    
    Args:
        phone_number: Phone number to call
        room_name: Optional room name
        agent_name: Agent name to dispatch
        
    Returns:
        Call initiation result
    """
    manager = CallManager()
    return await manager.initiate_call(phone_number, room_name, agent_name)


if __name__ == "__main__":
    # Simple test - call a number from command line
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python call_manager.py <phone_number>")
        sys.exit(1)
    
    number = sys.argv[1]
    print(f"Initiating call to {number}...")
    
    try:
        result = asyncio.run(make_call(number))
        print(f"Call initiated successfully!")
        print(f"Room: {result['room_name']}")
        print(f"Dispatch ID: {result['dispatch_id']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)