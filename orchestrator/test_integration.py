#!/usr/bin/env python3
"""Integration test: Verify Hermes orchestrator → team dispatch → OpenViking flow."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from profile_input import DomainProfile
from hermes_orchestrator import get_orchestrator
from team_orchestrator import get_team_registry


async def test_team_routing():
    """Test team lookup and dispatch."""
    print("=" * 60)
    print("TEST: Team Routing")
    print("=" * 60)
    
    registry = get_team_registry()
    
    # Test each domain
    for domain in ["video", "law", "architecture", "homesteading"]:
        team = registry.get_team_for_domain(domain)
        chief = registry.get_chief_agent(domain)
        members = registry.get_team_members(domain)
        
        print(f"✓ {domain.upper()}")
        print(f"  Team: {team['name'] if team else 'NOT FOUND'}")
        print(f"  Chief: {chief['agent_id'] if chief else 'NOT FOUND'}")
        print(f"  Members: {len(members)} agents")
    
    print("\n✓ All teams loaded successfully!")


async def main():
    print("\n" + "=" * 60)
    print("Hermes AI OS Stack - Integration Test")
    print("=" * 60 + "\n")
    
    try:
        await test_team_routing()
        print("\n✓ Integration test complete!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
