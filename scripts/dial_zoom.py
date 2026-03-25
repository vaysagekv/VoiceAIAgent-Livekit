"""Script to dispatch agent to join a Zoom meeting."""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from livekit import api

load_dotenv(".env.local")


async def main():
    """Dispatch the Zoom dialing agent to a meeting."""
    lkapi = api.LiveKitAPI()
    
    # Meeting details - can be passed as arguments or use defaults
    import argparse
    parser = argparse.ArgumentParser(description='Dispatch AI agent to join a Zoom meeting')
    parser.add_argument('--meeting-id', type=str, help='Zoom meeting ID')
    parser.add_argument('--password', type=str, default='', help='Zoom meeting password')
    parser.add_argument('--room', type=str, help='LiveKit room name (optional)')
    args = parser.parse_args()
    
    # Get meeting details from args or environment
    meeting_id = args.meeting_id or os.getenv("ZOOM_MEETING_ID")
    meeting_password = args.password or os.getenv("ZOOM_MEETING_PASSWORD", "")
    
    if not meeting_id:
        print("Error: No meeting ID provided. Use --meeting-id or set ZOOM_MEETING_ID in .env.local")
        print("\nUsage examples:")
        print("  python scripts/dial_zoom.py --meeting-id 1234567890")
        print("  python scripts/dial_zoom.py --meeting-id 1234567890 --password secret123")
        print("  python scripts/dial_zoom.py --meeting-id 1234567890 --room my-demo-room")
        sys.exit(1)
    
    # Generate room name if not provided
    room_name = args.room or f"zoom-meeting-{meeting_id}"
    
    print(f"Dispatching agent to Zoom meeting: {meeting_id}")
    print(f"Room: {room_name}")
    
    try:
        # Dispatch agent
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name="zoom-dialing-agent",
                room=room_name,
                metadata=f'{{"meeting_id": "{meeting_id}", "meeting_password": "{meeting_password}"}}'
            )
        )
        
        print(f"\n✅ Agent dispatched successfully!")
        print(f"   Dispatch ID: {dispatch.id}")
        print(f"   Room: {dispatch.room}")
        print(f"   Agent: {dispatch.agent_name}")
        print(f"\nThe agent will join the Zoom meeting shortly.")
        print("You should see 'AI Agent' appear as a phone participant in Zoom.")
        
    except Exception as e:
        print(f"\n❌ Error dispatching agent: {e}")
        print("\nTroubleshooting:")
        print("  - Ensure the agent is running: python src/zoom_dialer.py dev")
        print("  - Check that ZOOM_SIP_TRUNK_ID is configured in .env.local")
        print("  - Verify LiveKit API credentials are set")
        sys.exit(1)
    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    asyncio.run(main())