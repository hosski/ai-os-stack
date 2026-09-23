"""
Team Orchestration Layer: Chiefs of Staff manage domain teams via Executor.

Each team (Video, Law, Architecture, Homesteading) has a Chief of Staff agent
that reads the team topology from Fruvisi and disseminates work to team members.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TEAMS_CONFIG_PATH = Path.home() / ".hermes" / "fruvisi" / "ai-os-stack-teams.json"


class FruvisiTeamRegistry:
    """Manages team topology and Chief of Staff routing."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or TEAMS_CONFIG_PATH
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load team topology from ai-os-stack-teams.json."""
        if not self.config_path.exists():
            logger.warning(f"Team config not found at {self.config_path}")
            return
        
        try:
            with open(self.config_path) as f:
                self.config = json.load(f)
            logger.info(f"Loaded team topology from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load team config: {e}")
    
    def get_team_for_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get team config for a domain."""
        routing = self.config.get("domain_routing", {})
        route = routing.get(domain)
        if not route:
            return None
        
        team_name = route.get("team")
        teams = self.config.get("teams", {})
        team = teams.get(team_name)
        
        if team:
            team["domain"] = domain
            team["routing"] = route
        
        return team
    
    def get_chief_agent(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get Chief of Staff agent for a domain."""
        team = self.get_team_for_domain(domain)
        if not team:
            return None
        
        chief_name = team.get("chief_of_staff")
        agents = self.config.get("agents", {})
        chief = agents.get(chief_name)
        
        if chief:
            chief["agent_id"] = chief_name
            chief["team"] = team.get("name")
        
        return chief
    
    def get_team_members(self, domain: str) -> List[Dict[str, Any]]:
        """Get all member agents for a team."""
        team = self.get_team_for_domain(domain)
        if not team:
            return []
        
        member_names = team.get("members", [])
        agents = self.config.get("agents", {})
        
        members = []
        for name in member_names:
            agent = agents.get(name)
            if agent:
                agent["agent_id"] = name
                members.append(agent)
        
        return members


class TeamDispatcher:
    """Dispatches tasks to team Chiefs of Staff."""
    
    def __init__(self, team_registry: Optional[FruvisiTeamRegistry] = None):
        self.registry = team_registry or FruvisiTeamRegistry()
    
    async def dispatch_to_team(
        self,
        domain: str,
        task_type: str,
        task_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch task to team Chief of Staff."""
        chief = self.registry.get_chief_agent(domain)
        if not chief:
            raise RuntimeError(f"No Chief of Staff found for domain {domain}")
        
        members = self.registry.get_team_members(domain)
        
        dispatch = {
            "domain": domain,
            "task_type": task_type,
            "task_payload": task_payload,
            "chief_of_staff": chief,
            "team_members": members,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        logger.info(f"Dispatching to Chief: {chief['agent_id']} with {len(members)} team members")
        return dispatch


_registry: Optional[FruvisiTeamRegistry] = None
_dispatcher: Optional[TeamDispatcher] = None


def get_team_registry() -> FruvisiTeamRegistry:
    global _registry
    if _registry is None:
        _registry = FruvisiTeamRegistry()
    return _registry


def get_team_dispatcher() -> TeamDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = TeamDispatcher(get_team_registry())
    return _dispatcher


async def dispatch_to_team_chief(
    domain: str,
    task_type: str,
    task_payload: Dict[str, Any],
) -> Dict[str, Any]:
    dispatcher = get_team_dispatcher()
    return await dispatcher.dispatch_to_team(domain, task_type, task_payload)
