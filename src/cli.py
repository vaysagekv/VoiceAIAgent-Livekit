"""Command-line interface for the Voice AI Caller."""

import asyncio
import sys
from typing import Optional

import click
from dotenv import load_dotenv

from src.call_manager import CallManager

# Load environment variables
load_dotenv(".env.local")


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Voice AI CLI - Make AI-powered phone calls."""
    pass


@cli.command()
@click.argument("phone_number")
@click.option(
    "--room-name",
    "-r",
    help="Custom room name (auto-generated if not provided)",
)
@click.option(
    "--agent-name",
    "-a",
    default="casual-caller",
    help="Name of the agent to dispatch",
)
@click.option(
    "--metadata",
    "-m",
    help="JSON metadata to pass to the agent",
)
@click.option(
    "--wait",
    is_flag=True,
    help="Wait for call to complete (blocks until call ends)",
)
def call(
    phone_number: str,
    room_name: Optional[str],
    agent_name: str,
    metadata: Optional[str],
    wait: bool,
):
    """Make an outbound phone call to PHONE_NUMBER.
    
    Example:
        voice-ai call +15551234567
    
    The agent will call the number and have a casual conversation.
    The user can end the call by saying goodbye or the agent will
    end it after a natural conclusion.
    """
    ctx = click.get_current_context()
    
    # Parse optional metadata
    call_metadata = {}
    if metadata:
        import json
        try:
            call_metadata = json.loads(metadata)
        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON metadata - {e}", err=True)
            ctx.exit(1)
    
    # Initialize call manager
    try:
        manager = CallManager()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("\nMake sure you have set up your .env.local file with:", err=True)
        click.echo("  - LIVEKIT_URL", err=True)
        click.echo("  - LIVEKIT_API_KEY", err=True)
        click.echo("  - LIVEKIT_API_SECRET", err=True)
        click.echo("  - SIP_OUTBOUND_TRUNK_ID", err=True)
        ctx.exit(1)
    
    # Validate phone number
    if not manager.validate_phone_number(phone_number):
        click.echo(f"Error: Invalid phone number format: {phone_number}", err=True)
        click.echo("Phone number should be in E.164 format (e.g., +15551234567)", err=True)
        ctx.exit(1)
    
    # Initiate the call
    click.echo(f"📞 Initiating call to {phone_number}...")
    
    try:
        result = asyncio.run(
            manager.initiate_call(
                phone_number=phone_number,
                room_name=room_name,
                agent_name=agent_name,
                metadata=call_metadata,
            )
        )
        
        click.echo(f"✅ Call initiated successfully!")
        click.echo(f"   Room: {result['room_name']}")
        click.echo(f"   Dispatch ID: {result['dispatch_id']}")
        click.echo(f"   Agent: {result['agent_name']}")
        
        if wait:
            click.echo("\n⏳ Waiting for call to complete...")
            click.echo("   (Press Ctrl+C to stop waiting)")
            
            # Keep alive until interrupted
            try:
                while True:
                    asyncio.run(asyncio.sleep(1))
            except KeyboardInterrupt:
                click.echo("\n👋 Stopped waiting for call.")
        
    except Exception as e:
        click.echo(f"❌ Error initiating call: {e}", err=True)
        ctx.exit(1)


@cli.command()
def configure():
    """Show configuration status and setup guide."""
    from dotenv import dotenv_values
    
    click.echo("Voice AI CLI Configuration")
    click.echo("=" * 40)
    
    # Check current configuration
    env_vars = dotenv_values(".env.local")
    
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "SIP_OUTBOUND_TRUNK_ID",
    ]
    
    all_set = True
    
    for var in required_vars:
        value = env_vars.get(var)
        if value and not value.startswith("your-") and not value.startswith("ST_xxxx"):
            click.echo(f"✅ {var}: Set")
        else:
            click.echo(f"❌ {var}: Not set")
            all_set = False
    
    if all_set:
        click.echo("\n✅ Configuration complete! Ready to make calls.")
    else:
        click.echo("\n⚠️  Configuration incomplete")
        click.echo("\nSetup Instructions:")
        click.echo("1. Create a LiveKit Cloud account at https://cloud.livekit.io")
        click.echo("2. Create a project and copy credentials to .env.local")
        click.echo("3. Set up a SIP trunk (Twilio, Telnyx, etc.)")
        click.echo("4. Add the SIP_OUTBOUND_TRUNK_ID to .env.local")


@cli.command()
@click.argument("phone_number")
def validate(phone_number: str):
    """Validate a phone number format."""
    manager = CallManager()
    
    normalized = manager._normalize_phone_number(phone_number)
    is_valid = manager.validate_phone_number(phone_number)
    
    click.echo(f"Original: {phone_number}")
    click.echo(f"Normalized: {normalized}")
    click.echo(f"Valid: {'✅ Yes' if is_valid else '❌ No'}")
    
    if not is_valid:
        click.echo("\nPhone numbers should be in E.164 format:")
        click.echo("  - Start with + followed by country code")
        click.echo("  - Example: +15551234567 (US number)")
        click.echo("  - Example: +447911123456 (UK number)")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()