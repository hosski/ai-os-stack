"""
OpenViking Audit Dashboard: Full execution timeline + metrics.

Queries OpenViking for:
1. Task execution DAG + tiers
2. Per-tier execution times
3. Sub-agent results (success/failure)
4. Parallelization efficiency (actual vs. optimal)
5. Critical path analysis
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class ExecutionAuditDashboard:
    """Builds an audit dashboard from task execution history."""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.events: List[Dict[str, Any]] = []
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add execution event."""
        self.events.append(event)
    
    def compute_metrics(self) -> Dict[str, Any]:
        """Compute execution metrics from events."""
        
        # Timeline
        start_time = None
        end_time = None
        
        for event in self.events:
            ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            if start_time is None:
                start_time = ts
            end_time = ts
        
        total_duration = (end_time - start_time).total_seconds() / 60 if start_time and end_time else 0
        
        # Per-tier metrics
        tier_metrics = {}
        for event in self.events:
            if event.get("state") == "tier_complete":
                tier_id = event["payload"].get("tier")
                tier_metrics[tier_id] = {
                    "tasks": event["payload"].get("tasks_completed", 0),
                    "duration_seconds": event["payload"].get("duration_seconds", 0),
                    "parallelized": event["payload"].get("parallelized", False),
                }
        
        # Parallelization efficiency
        critical_path_time = sum(m["duration_seconds"] for m in tier_metrics.values()) / 60
        parallel_speedup = total_duration / critical_path_time if critical_path_time > 0 else 1.0
        
        # Sub-agent success rate
        sub_agent_events = [e for e in self.events if e.get("state") == "sub_agent_complete"]
        successful = sum(1 for e in sub_agent_events if e["payload"].get("success", False))
        total_sub_agents = len(sub_agent_events)
        success_rate = successful / total_sub_agents if total_sub_agents > 0 else 0
        
        return {
            "total_duration_minutes": total_duration,
            "critical_path_minutes": critical_path_time,
            "parallelization_speedup": parallel_speedup,
            "sub_agent_success_rate": success_rate,
            "tier_metrics": tier_metrics,
            "num_sub_agents": total_sub_agents,
            "num_successful": successful,
            "num_failed": total_sub_agents - successful,
        }
    
    def render_html_dashboard(self) -> str:
        """Render an HTML dashboard for OpenViking/Fruvisi."""
        
        metrics = self.compute_metrics()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Task Execution Audit: {self.task_id}</title>
    <style>
        body {{ font-family: monospace; background: #0a0e27; color: #e0e0e0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ border-bottom: 2px solid #00ff00; padding-bottom: 10px; margin-bottom: 20px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .metric {{ background: #1a1f3a; border: 1px solid #00ff00; padding: 15px; border-radius: 5px; }}
        .metric-title {{ color: #00ff00; font-size: 12px; text-transform: uppercase; }}
        .metric-value {{ font-size: 28px; color: #00ff88; margin-top: 5px; }}
        .tier {{ background: #1a1f3a; border: 1px solid #0088ff; padding: 15px; margin-bottom: 10px; border-radius: 5px; }}
        .tier-header {{ color: #0088ff; font-weight: bold; margin-bottom: 10px; }}
        .sub-agent {{ padding-left: 20px; margin: 5px 0; }}
        .success {{ color: #00ff88; }}
        .failure {{ color: #ff0044; }}
        .timeline {{ margin-top: 30px; }}
        .event {{ padding: 10px; margin: 5px 0; background: #0f1428; border-left: 3px solid #00ff00; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎸 Task Execution Audit Dashboard</h1>
            <p>Task ID: <code>{self.task_id}</code></p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric">
                <div class="metric-title">Total Duration</div>
                <div class="metric-value">{metrics["total_duration_minutes"]:.1f}m</div>
            </div>
            <div class="metric">
                <div class="metric-title">Critical Path</div>
                <div class="metric-value">{metrics["critical_path_minutes"]:.1f}m</div>
            </div>
            <div class="metric">
                <div class="metric-title">Speedup</div>
                <div class="metric-value">{metrics["parallelization_speedup"]:.2f}x</div>
            </div>
            <div class="metric">
                <div class="metric-title">Sub-Agent Success</div>
                <div class="metric-value success">{metrics["sub_agent_success_rate"]:.0%}</div>
            </div>
        </div>
        
        <h2>Tier Execution Timeline</h2>
        <div class="tiers">
"""
        
        for tier_id, tier_data in sorted(metrics["tier_metrics"].items()):
            html += f"""
            <div class="tier">
                <div class="tier-header">Tier {tier_id} {"[PARALLEL]" if tier_data["parallelized"] else "[SEQUENTIAL]"}</div>
                <div>Tasks completed: {tier_data["tasks"]}</div>
                <div>Duration: {tier_data["duration_seconds"] / 60:.1f} minutes</div>
            </div>
"""
        
        html += """
        </div>
        
        <h2>Execution Events</h2>
        <div class="timeline">
"""
        
        for event in self.events:
            state = event.get("state", "unknown")
            payload = event.get("payload", {})
            html += f"""
            <div class="event">
                <strong>[{state}]</strong> {event.get("timestamp", "unknown")}
                <pre>{json.dumps(payload, indent=2)}</pre>
            </div>
"""
        
        html += """
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def render_ascii_summary(self) -> str:
        """Render ASCII summary."""
        
        metrics = self.compute_metrics()
        
        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║              TASK EXECUTION AUDIT DASHBOARD                  ║
╚══════════════════════════════════════════════════════════════╝

Task ID: {self.task_id}

┌─ EXECUTION METRICS ─────────────────────────────────────────┐
│                                                              │
│  Total Duration:        {metrics["total_duration_minutes"]:.1f} minutes                   │
│  Critical Path:         {metrics["critical_path_minutes"]:.1f} minutes                   │
│  Parallelization:       {metrics["parallelization_speedup"]:.2f}x speedup                    │
│  Sub-Agent Success:     {metrics["sub_agent_success_rate"]:.0%}                       │
│                                                              │
│  Sub-Agents Executed:   {metrics["num_sub_agents"]}                         │
│  Successful:            {metrics["num_successful"]}                         │
│  Failed:                {metrics["num_failed"]}                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌─ TIER EXECUTION TIMELINE ───────────────────────────────────┐
│                                                              │
"""
        
        max_time = max((m["duration_seconds"] for m in metrics["tier_metrics"].values()), default=1)
        
        for tier_id in sorted(metrics["tier_metrics"].keys()):
            tier_data = metrics["tier_metrics"][tier_id]
            bar_length = int((tier_data["duration_seconds"] / max_time) * 40)
            bar = "█" * bar_length
            parallel_tag = "[PAR]" if tier_data["parallelized"] else "[SEQ]"
            
            summary += f"│  Tier {tier_id} {parallel_tag:6s} {bar:<40s} {tier_data['duration_seconds']/60:.1f}m\n"
        
        summary += """│                                                              │
└──────────────────────────────────────────────────────────────┘

OpenViking URI: viking://user/default/tasks/{task_id}/
Fruvisi Link:   /fruvisi/task/{task_id}/audit
"""
        
        return summary


def create_audit_dashboard_html(task_id: str, events: List[Dict[str, Any]]) -> str:
    """Factory function to create audit dashboard HTML."""
    
    dashboard = ExecutionAuditDashboard(task_id)
    for event in events:
        dashboard.add_event(event)
    
    return dashboard.render_html_dashboard()


def create_audit_dashboard_ascii(task_id: str, events: List[Dict[str, Any]]) -> str:
    """Factory function to create audit dashboard ASCII."""
    
    dashboard = ExecutionAuditDashboard(task_id)
    for event in events:
        dashboard.add_event(event)
    
    return dashboard.render_ascii_summary()
