"""
Daily Momentum Engine: Auto-dispatch tasks every morning, measure speedup, ship daily.

Features:
  1. Auto-load yesterday's completed tasks from OpenViking
  2. Extract patterns (domain, complexity, parallelization effectiveness)
  3. Generate today's batch (grill-tab-5 suggestions based on patterns)
  4. Dispatch tier-by-tier (Chief orchestration)
  5. Measure actual vs. predicted speedup
  6. Post daily metrics dashboard (Slack/Discord/terminal)
  7. Learn from rework loops (QA failures → faster reruns next time)

Daily flow:
  6:00 AM → Load yesterday's metrics
  6:05 AM → Suggest today's tasks (AI-generated or user-picked)
  6:15 AM → Execute batch (all domains in parallel)
  6:30 AM → Stream progress (SSE → terminal/dashboard)
  5:00 PM → Aggregate results + metrics
  5:05 PM → Post daily report (speedup %, time saved, quality score)
  5:10 PM → Archive to OpenViking + learn patterns

Metrics tracked:
  - Predicted time vs. actual time (speedup %)
  - Tasks completed per day
  - Sub-agent success rate (per role)
  - QA pass rate (first time vs. rework)
  - Cost (token count per task)
  - Parallelization efficiency (% of theoretical max)
  - Team velocity (tasks/hour)
"""

import asyncio
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DailyMetrics:
    """Daily performance snapshot."""
    date: str  # YYYY-MM-DD
    tasks_completed: int
    avg_speedup: float  # 1.5x, 2x, etc.
    time_saved_hours: float
    qa_pass_rate: float  # 0-1
    total_tokens: int
    parallelization_efficiency: float  # 0-1
    team_velocity: float  # tasks/hour
    domains_executed: list[str]
    critical_tasks_completed: list[str]  # High-impact tasks
    rework_count: int
    rework_rate: float  # rework/total
    

@dataclass
class MomentumPattern:
    """Learned pattern from prior days."""
    domain: str  # "video", "architecture", etc.
    complexity: str  # "low", "medium", "high"
    avg_speedup: float
    recommended_parallelization: int  # Suggested parallel agents
    estimated_time_hours: float
    typical_rework_rate: float


class DailyMomentumEngine:
    """Rock and roll every day."""
    
    def __init__(self, openviking_client, executor_integration, hermes_orchestrator):
        self.openviking = openviking_client
        self.executor = executor_integration
        self.orchestrator = hermes_orchestrator
        self.patterns: dict[str, MomentumPattern] = {}
        
    async def morning_briefing(self) -> dict:
        """6:00 AM: Load yesterday's metrics + suggest today's tasks."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Get yesterday's metrics
        yesterday_metrics = await self._load_daily_metrics(yesterday)
        logger.info(f"Yesterday's speedup: {yesterday_metrics.avg_speedup:.2f}x")
        
        # Extract patterns
        self.patterns = await self._extract_patterns(yesterday_metrics)
        
        # Generate suggestions for today
        suggestions = await self._suggest_daily_batch(yesterday_metrics)
        
        return {
            "yesterday": asdict(yesterday_metrics),
            "patterns": {k: asdict(v) for k, v in self.patterns.items()},
            "today_suggestions": suggestions,
            "momentum_score": self._calculate_momentum_score(yesterday_metrics),
        }
    
    async def execute_daily_batch(self, tasks: list[dict]) -> dict:
        """6:15 AM: Execute all tasks in parallel (by domain)."""
        start_time = time.time()
        
        # Group tasks by domain
        by_domain = {}
        for task in tasks:
            domain = task["domain"]
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(task)
        
        # Dispatch all domains in parallel
        coroutines = [
            self._execute_domain_batch(domain, domain_tasks)
            for domain, domain_tasks in by_domain.items()
        ]
        results = await asyncio.gather(*coroutines)
        
        execution_time = time.time() - start_time
        
        return {
            "batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "domains_executed": list(by_domain.keys()),
            "results": results,
            "wall_clock_time": execution_time,
            "status": "completed",
        }
    
    async def _execute_domain_batch(self, domain: str, tasks: list[dict]) -> dict:
        """Execute all tasks for one domain (Chief orchestrates)."""
        logger.info(f"Dispatching {len(tasks)} tasks to {domain} team")
        
        # Dispatch to Chief
        pattern = self.patterns.get(domain)
        parallelization = pattern.recommended_parallelization if pattern else 4
        
        result = await self.orchestrator.dispatch_task_dag(
            domain=domain,
            tasks=tasks,
            config={
                "max_parallel_agents": parallelization,
                "enable_parallelization": True,
                "tier_timeout_multiplier": 1.5,
            }
        )
        
        return result
    
    async def _load_daily_metrics(self, date: str) -> DailyMetrics:
        """Load yesterday's metrics from OpenViking."""
        uri = f"viking://user/default/metrics/daily/{date}.json"
        content = await self.openviking.read(uri)
        
        if not content:
            # Default if no data
            return DailyMetrics(
                date=date,
                tasks_completed=0,
                avg_speedup=1.0,
                time_saved_hours=0,
                qa_pass_rate=1.0,
                total_tokens=0,
                parallelization_efficiency=0.5,
                team_velocity=0.0,
                domains_executed=[],
                critical_tasks_completed=[],
                rework_count=0,
                rework_rate=0.0,
            )
        
        data = json.loads(content)
        return DailyMetrics(**data)
    
    async def _extract_patterns(self, metrics: DailyMetrics) -> dict[str, MomentumPattern]:
        """Learn patterns from recent history."""
        patterns = {}
        
        for domain in metrics.domains_executed:
            # Query last 7 days for this domain
            domain_metrics = await self._get_domain_history(domain, days=7)
            
            if domain_metrics:
                avg_speedup = sum(m.avg_speedup for m in domain_metrics) / len(domain_metrics)
                avg_parallelization = 4 if avg_speedup > 1.7 else 3
                
                patterns[domain] = MomentumPattern(
                    domain=domain,
                    complexity="medium",  # TODO: infer from task complexity
                    avg_speedup=avg_speedup,
                    recommended_parallelization=avg_parallelization,
                    estimated_time_hours=8.0,  # Baseline
                    typical_rework_rate=0.1,
                )
        
        return patterns
    
    async def _suggest_daily_batch(self, yesterday: DailyMetrics) -> list[dict]:
        """AI-generate suggestions based on patterns + user velocity."""
        suggestions = []
        
        for domain, pattern in self.patterns.items():
            # Suggest task if domain showed good speedup yesterday
            if pattern.avg_speedup > 1.5:
                suggestions.append({
                    "domain": domain,
                    "reason": f"Yesterday: {pattern.avg_speedup:.2f}x speedup",
                    "estimated_duration_hours": pattern.estimated_time_hours,
                    "estimated_speedup": pattern.avg_speedup,
                    "parallelization": pattern.recommended_parallelization,
                })
        
        return suggestions
    
    async def _get_domain_history(self, domain: str, days: int = 7) -> list[DailyMetrics]:
        """Fetch last N days of metrics for a domain."""
        metrics = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            m = await self._load_daily_metrics(date)
            if domain in m.domains_executed:
                metrics.append(m)
        return metrics
    
    async def evening_report(self, batch_result: dict) -> dict:
        """5:00 PM: Aggregate results + post daily report."""
        total_tasks = sum(len(r.get("tasks", [])) for r in batch_result.get("results", []))
        total_time = batch_result.get("wall_clock_time", 0)
        
        # Calculate metrics
        metrics = DailyMetrics(
            date=datetime.now().strftime("%Y-%m-%d"),
            tasks_completed=total_tasks,
            avg_speedup=self._calculate_avg_speedup(batch_result),
            time_saved_hours=self._calculate_time_saved(batch_result),
            qa_pass_rate=self._calculate_qa_pass_rate(batch_result),
            total_tokens=self._sum_tokens(batch_result),
            parallelization_efficiency=self._calculate_parallelization_efficiency(batch_result),
            team_velocity=total_tasks / (total_time / 3600) if total_time > 0 else 0,
            domains_executed=batch_result.get("domains_executed", []),
            critical_tasks_completed=self._find_critical_tasks(batch_result),
            rework_count=self._count_reworks(batch_result),
            rework_rate=self._calculate_rework_rate(batch_result),
        )
        
        # Store in OpenViking
        await self._store_daily_metrics(metrics)
        
        # Generate report
        report = self._generate_report(metrics)
        
        return report
    
    def _calculate_momentum_score(self, metrics: DailyMetrics) -> float:
        """0-10 score: speedup + velocity + quality."""
        speedup_score = min(metrics.avg_speedup, 3.0) / 3.0 * 3
        velocity_score = min(metrics.team_velocity, 5.0) / 5.0 * 3
        quality_score = metrics.qa_pass_rate * 4
        return speedup_score + velocity_score + quality_score
    
    def _calculate_avg_speedup(self, batch_result: dict) -> float:
        """Average speedup across all tasks."""
        speedups = []
        for result in batch_result.get("results", []):
            if "speedup" in result:
                speedups.append(result["speedup"])
        return sum(speedups) / len(speedups) if speedups else 1.0
    
    def _calculate_time_saved(self, batch_result: dict) -> float:
        """Total hours saved vs. sequential."""
        total_actual = batch_result.get("wall_clock_time", 0) / 3600
        speedup = self._calculate_avg_speedup(batch_result)
        sequential_time = total_actual * speedup
        return sequential_time - total_actual
    
    def _calculate_qa_pass_rate(self, batch_result: dict) -> float:
        """% of tasks passing QA first time."""
        total = 0
        passed = 0
        for result in batch_result.get("results", []):
            for task_result in result.get("tasks", []):
                total += 1
                if task_result.get("qa_verdict") == "pass":
                    passed += 1
        return passed / total if total > 0 else 1.0
    
    def _sum_tokens(self, batch_result: dict) -> int:
        """Total tokens used across all sub-agents."""
        total = 0
        for result in batch_result.get("results", []):
            for task_result in result.get("tasks", []):
                total += task_result.get("tokens_used", 0)
        return total
    
    def _calculate_parallelization_efficiency(self, batch_result: dict) -> float:
        """Actual speedup / theoretical max."""
        actual_speedup = self._calculate_avg_speedup(batch_result)
        # Theoretical max: num_parallel_cores
        theoretical_max = 8  # M5 performance cores
        return min(actual_speedup / theoretical_max, 1.0)
    
    def _find_critical_tasks(self, batch_result: dict) -> list[str]:
        """High-impact tasks completed."""
        critical = []
        for result in batch_result.get("results", []):
            for task_result in result.get("tasks", []):
                if task_result.get("priority") == "critical":
                    critical.append(task_result.get("task_id", "unknown"))
        return critical
    
    def _count_reworks(self, batch_result: dict) -> int:
        """Tasks that needed rework (QA fail)."""
        count = 0
        for result in batch_result.get("results", []):
            for task_result in result.get("tasks", []):
                if task_result.get("qa_verdict") != "pass":
                    count += 1
        return count
    
    def _calculate_rework_rate(self, batch_result: dict) -> float:
        """% of tasks needing rework."""
        total = sum(len(r.get("tasks", [])) for r in batch_result.get("results", []))
        rework_count = self._count_reworks(batch_result)
        return rework_count / total if total > 0 else 0.0
    
    async def _store_daily_metrics(self, metrics: DailyMetrics):
        """Save to OpenViking."""
        uri = f"viking://user/default/metrics/daily/{metrics.date}.json"
        await self.openviking.write(uri, json.dumps(asdict(metrics), indent=2))
    
    def _generate_report(self, metrics: DailyMetrics) -> dict:
        """5:05 PM: Generate beautiful daily report."""
        report_text = f"""
🎸 DAILY MOMENTUM REPORT — {metrics.date} 🎸
═══════════════════════════════════════════════════════════════

📊 METRICS
  Tasks Completed: {metrics.tasks_completed}
  Speedup: {metrics.avg_speedup:.2f}x
  Time Saved: {metrics.time_saved_hours:.1f} hours
  QA Pass Rate: {metrics.qa_pass_rate * 100:.0f}%
  Team Velocity: {metrics.team_velocity:.2f} tasks/hour

⚡ PARALLELIZATION
  Efficiency: {metrics.parallelization_efficiency * 100:.0f}% of theoretical max
  Tokens Used: {metrics.total_tokens:,}
  Rework Rate: {metrics.rework_rate * 100:.0f}%

🎯 DOMAINS
  {', '.join(metrics.domains_executed)}

🏆 CRITICAL TASKS
  {chr(10).join('  ✓ ' + t for t in metrics.critical_tasks_completed)}

📈 MOMENTUM TRAJECTORY
  Keep shipping at this pace to 10x productivity!

═══════════════════════════════════════════════════════════════
🎸 ROCK AND ROLL EVERY DAY 🎸
"""
        return {
            "date": metrics.date,
            "report_text": report_text,
            "metrics": asdict(metrics),
            "momentum_score": self._calculate_momentum_score(metrics),
        }


# Entry point: scheduler (cron job)
async def run_daily_momentum():
    """Called by hermes cron: `hermes cron schedule daily-momentum`"""
    # TODO: Wire real clients
    engine = DailyMomentumEngine(None, None, None)
    
    # 6:00 AM
    briefing = await engine.morning_briefing()
    print(f"Morning briefing: {json.dumps(briefing, indent=2)}")
    
    # 6:15 AM (user picks from suggestions or custom)
    tasks = briefing["today_suggestions"]  # or await user_input()
    
    # Execute
    batch_result = await engine.execute_daily_batch(tasks)
    
    # 5:00 PM
    report = await engine.evening_report(batch_result)
    print(report.get("report_text", ""))
    
    # Post to Slack/Discord/whatever
    await _post_report(report)


async def _post_report(report: dict):
    """Post to user's preferred notification channel."""
    # TODO: integrate with gateway.platforms
    logger.info(f"Report:\n{report.get('report_text', '')}")


if __name__ == "__main__":
    asyncio.run(run_daily_momentum())
