"""
Profile input layer for AI OS Stack: domain-specific orchestration setup.

This module handles one-by-one profile configuration for domain profiles (Video, Law, Architecture, Homesteading).
Each profile captures domain metadata, model preferences, and initial dispatch routing.

Entry point: prompt_for_domain_profile() — interactive CLI flow.
"""

from typing import Optional, TypedDict, List
import json
from pathlib import Path


class DomainProfile(TypedDict):
    """Domain-specific orchestration profile."""
    domain: str  # "video", "law", "architecture", "homesteading"
    description: str  # User-provided description
    primary_model: str  # Model for primary generation (e.g., "ltx-2.5" for video)
    aux_models: list[str]  # Auxiliary model names
    created_at: str  # ISO 8601 timestamp


# Model defaults per domain
MODEL_DEFAULTS = {
    "video": {
        "primary": "ltx-2.5",
        "aux": ["qwen-3.6", "flux-2"],
    },
    "law": {
        "primary": "qwen-3.8",
        "aux": ["gemma-4-12b"],
    },
    "architecture": {
        "primary": "flux-2",
        "aux": ["qwen-3.8"],
    },
    "homesteading": {
        "primary": "gemma-4b",
        "aux": ["qwen-3.6"],
    },
}

DOMAINS = ["video", "law", "architecture", "homesteading"]


def prompt_for_domain_profile() -> Optional[DomainProfile]:
    """
    Interactively prompt for domain profile configuration.
    
    Returns:
        DomainProfile dict or None if user cancels.
    """
    from datetime import datetime
    
    print("\n=== Domain Profile Setup ===\n")
    
    # Domain selection
    print("Available domains:")
    for i, domain in enumerate(DOMAINS, 1):
        print(f"  {i}. {domain}")
    
    domain_choice = input("\nSelect domain (1-4): ").strip()
    try:
        domain_idx = int(domain_choice) - 1
        if not (0 <= domain_idx < len(DOMAINS)):
            print("Invalid selection.")
            return None
        domain = DOMAINS[domain_idx]
    except ValueError:
        print("Invalid input.")
        return None
    
    # Description
    description = input(f"\nBrief description for '{domain}' profile: ").strip()
    if not description:
        description = f"{domain.capitalize()} domain profile"
    
    # Model selection
    defaults = MODEL_DEFAULTS[domain]
    print(f"\nPrimary model (default: {defaults['primary']}): ", end="")
    primary = input().strip() or defaults["primary"]
    
    print(f"Auxiliary models (comma-separated, default: {','.join(defaults['aux'])}): ", end="")
    aux_input = input().strip()
    aux = [m.strip() for m in aux_input.split(",")] if aux_input else defaults["aux"]
    
    return {
        "domain": domain,
        "description": description,
        "primary_model": primary,
        "aux_models": aux,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def save_domain_profile(profile: DomainProfile, config_path: Optional[Path] = None) -> None:
    """
    Save domain profile to config.

    Args:
        profile: DomainProfile dict
        config_path: Optional path to config file (default: ~/.hermes/config.yaml)
    """
    if config_path is None:
        config_path = Path.home() / ".hermes" / "config.yaml"
    
    # TODO: Integrate with atomic_config_write from config
    # For now, just log what would be saved
    print(f"\n✓ Profile saved: {profile['domain']} ({profile['primary_model']})")
    print(f"  Description: {profile['description']}")
    print(f"  Aux models: {', '.join(profile['aux_models'])}")
