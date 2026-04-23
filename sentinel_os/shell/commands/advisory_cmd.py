from rich.console import Console
from rich.table import Table

def cmd_advisory(sim, console: Console):
    """Display AI fault risk assessment for all running tasks."""
    ai_advisor = sim.ai_advisor
    if not ai_advisor:
        console.print("[red]AI Advisor not loaded.[/red]")
        return

    console.print("\n[bold cyan]  AI ADVISORY ENGINE — RandomForest Fault Predictor[/bold cyan]")
    console.print(f"  Model: RandomForest | Features: 7 | Precision: {ai_advisor.precision:.1%}\n")
    
    tasks = sim.get_all_tasks()
    mem_pressure = sim.resource_manager.stats().get('memory_pressure_numeric', 20)
    
    table = Table(box=None, padding=(0, 2))
    table.add_column("Service", style="white", width=22)
    table.add_column("Fault Risk", width=14)
    table.add_column("Confidence", width=14)
    table.add_column("AI Boost", width=12)
    table.add_column("Action", width=20)
    
    table.add_section()
    
    for task in tasks:
        features = ai_advisor.extract_features(task, mem_pressure)
        prob = ai_advisor.predict_fault_probability(features)
        boost = ai_advisor.calculate_boost(prob)
        
        if prob > 0.7:
            risk_str = "[bold red]HIGH[/bold red]"
            action = "Priority elevated"
        elif prob > 0.4:
            risk_str = "[bold yellow]MEDIUM[/bold yellow]"
            action = "Monitoring"
        else:
            risk_str = "[bold green]LOW[/bold green]"
            action = "No action"
        
        table.add_row(
            task.task_type, 
            risk_str, 
            f"{prob:.1%}", 
            f"+{boost}", 
            action
        )
    
    console.print(table)
    console.print(f"\n  Top fault signal: [yellow]{ai_advisor.top_feature()}[/yellow]")
    console.print(f"  Scheduler notified. Hybrid mode adjusts priorities automatically.\n")
