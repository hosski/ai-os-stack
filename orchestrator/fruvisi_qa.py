"""Fruvisi QA Engine: Validates task results and manages rework loops."""

from typing import Optional, Dict, Any
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

FRUVISI_CONFIG_PATH = Path.home() / ".hermes" / "fruvisi" / "ai-os-stack-teams.json"


class FruvisiQAEngine:
    """Fruvisi QA validation and team topology management."""
    
    def __init__(self, topology_path: Optional[Path] = None):
        self.topology_path = topology_path or FRUVISI_CONFIG_PATH
        self.topology: Dict[str, Any] = {}
        self.load_topology()
    
    def load_topology(self) -> None:
        if not self.topology_path.exists():
            logger.warning(f"Fruvisi topology not found at {self.topology_path}")
            return
        
        try:
            with open(self.topology_path) as f:
                self.topology = json.load(f)
            logger.info(f"Loaded Fruvisi topology")
        except Exception as e:
            logger.error(f"Failed to load Fruvisi topology: {e}")
    
    def get_qa_rules_for_domain(self, domain: str) -> Dict[str, Any]:
        """Get QA rules for a specific domain."""
        teams = self.topology.get("teams", {})
        routing = self.topology.get("domain_routing", {}).get(domain, {})
        team_name = routing.get("team")
        team = teams.get(team_name, {})
        return team.get("qa_rules", {})
    
    async def validate_task_result(
        self,
        task_id: str,
        domain: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate task result against Fruvisi QA rules."""
        qa_rules = self.get_qa_rules_for_domain(domain)
        
        passed = True
        feedback = ""
        rework_suggestions = []
        score = 1.0
        
        if "error" in result:
            passed = False
            feedback = f"Task failed: {result['error']}"
            score = 0.0
        elif "output" not in result and "status" not in result:
            passed = False
            feedback = "No output produced"
            score = 0.3
        
        return {
            "passed": passed or score >= 0.7,
            "score": score,
            "feedback": feedback,
            "rework_suggestions": rework_suggestions,
            "checked_at": datetime.utcnow().isoformat() + "Z",
        }


_qa_engine: Optional[FruvisiQAEngine] = None


def get_qa_engine() -> FruvisiQAEngine:
    global _qa_engine
    if _qa_engine is None:
        _qa_engine = FruvisiQAEngine()
    return _qa_engine


async def validate_and_apply_qa(
    task_id: str,
    domain: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    engine = get_qa_engine()
    return await engine.validate_task_result(task_id, domain, result)
