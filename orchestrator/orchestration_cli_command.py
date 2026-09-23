"""
CLI command handler for profile setup and AI OS Stack initialization.

Slash command: /profile-setup
Starts interactive domain profile input and task dispatch.
"""

from typing import Optional
import asyncio
from profile_input import prompt_for_domain_profile
from hermes_orchestrator import get_orchestrator


async def handle_profile_setup_command() -> str:
    """
    Interactive profile setup and dispatch.
    
    Returns:
        Summary message
    """
    # Prompt for domain profile
    profile = prompt_for_domain_profile()
    if not profile:
        return "Profile setup cancelled."
    
    # Get orchestrator
    orch = get_orchestrator()
    
    # Example: dispatch a first task (e.g., for Video domain, generate initial content)
    if profile["domain"] == "video":
        task_type = "generate"
        input_payload = {
            "prompt": "Create a short children's series outline",
            "target_length": "3-5 episodes",
        }
    elif profile["domain"] == "law":
        task_type = "analyze"
        input_payload = {
            "document": "Sample legal brief",
        }
    elif profile["domain"] == "architecture":
        task_type = "design"
        input_payload = {
            "spec": "Modern sustainable home design",
        }
    else:  # homesteading
        task_type = "synthesize"
        input_payload = {
            "topic": "Off-grid water harvesting system",
        }
    
    # Dispatch task
    task_id = await orch.dispatch_task(profile, task_type, input_payload)
    
    return (
        f"✓ Profile '{profile['domain']}' created\n"
        f"  Primary model: {profile['primary_model']}\n"
        f"  Aux models: {', '.join(profile['aux_models'])}\n"
        f"\n✓ Dispatched initial task: {task_id}\n"
        f"  Type: {task_type}\n"
        f"  Status: pending (awaiting plugin execution)"
    )


async def main_cli_integration():
    """Main entry point for CLI slash command."""
    result = await handle_profile_setup_command()
    print(result)


if __name__ == "__main__":
    asyncio.run(main_cli_integration())
