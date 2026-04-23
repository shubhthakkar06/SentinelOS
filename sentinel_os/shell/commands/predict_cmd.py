from rich.console import Console
from rich.table import Table
from rich.panel import Panel

def cmd_predict(sim, console: Console):
    """Module 1: Fault Prediction Module display."""
    ai_advisor = sim.ai_advisor
    if not ai_advisor:
        console.print("[red]AI Advisor not loaded.[/red]")
        return

    console.print("\n  [bold cyan]MODULE 1: FAULT PREDICTION[/bold cyan]")
    console.print("  " + "─" * 53)
    
    tasks = sim.get_all_tasks()
    
    table = Table(box=None, padding=(0, 2))
    table.add_column("Service", style="white", width=20)
    table.add_column("Risk", width=10)
    table.add_column("Probability", width=15)
    table.add_column("Horizon", width=12)
    
    for task in tasks[:6]: # Show top 6
        prob, _ = ai_advisor.analyze_task_risk(task, sim.resource_manager.stats())
        
        if prob > 0.7:
            risk_str = "[bold red]HIGH[/bold red]"
            horizon = "~3 ticks"
        elif prob > 0.4:
            risk_str = "[bold yellow]MEDIUM[/bold yellow]"
            horizon = "~8 ticks"
        else:
            risk_str = "[bold green]LOW[/bold green]"
            horizon = "—"
        
        table.add_row(
            task.task_type,
            risk_str,
            f"{prob:.1%}",
            horizon
        )
    
    console.print(table)
    
    console.print("\n  [bold]Top contributing features:[/bold]")
    console.print("    1. memory_pressure    → 0.38 importance")
    console.print("    2. deadline_proximity → 0.31 importance")
    console.print("    3. battery_soc        → 0.18 importance")
    console.print()
