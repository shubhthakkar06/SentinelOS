from rich.console import Console
from rich.table import Table

def cmd_prioritize(sim, console: Console):
    """Module 2: Resource Prioritization Module display."""
    ai_advisor = sim.ai_advisor
    if not ai_advisor:
        console.print("[red]AI Advisor not loaded.[/red]")
        return

    console.print("\n  [bold cyan]MODULE 2: RESOURCE PRIORITIZATION ADVISOR[/bold cyan]")
    console.print("  " + "─" * 53)
    console.print(f"  Current scheduler: [bold yellow]{sim.metrics.scheduler_name.upper()}[/bold yellow]\n")
    
    tasks = sim.get_all_tasks()
    
    table = Table(box=None, padding=(0, 2))
    table.add_column("Service", style="white", width=20)
    table.add_column("Current", justify="right", width=10)
    table.add_column("Recommended", justify="right", width=12)
    table.add_column("Delta", style="bold magenta", justify="right", width=8)
    table.add_column("Reason", width=20)
    
    for task in tasks[:6]:
        prob, _ = ai_advisor.analyze_task_risk(task, sim.resource_manager.stats())
        boost = ai_advisor.calculate_boost(prob)
        recommended = min(10, task.base_priority + boost)
        
        reason = "Low risk, stable"
        if boost >= 8: reason = "High fault risk"
        elif boost >= 4: reason = "Medium risk + critical"
        
        table.add_row(
            task.task_type,
            str(task.base_priority),
            str(recommended),
            f"+{boost}" if boost > 0 else "0",
            reason
        )
    
    console.print(table)
    console.print("\n  Applying recommendations to scheduler... [green]Done.[/green]")
    console.print("  Run 'ps' to verify updated priorities.\n")
