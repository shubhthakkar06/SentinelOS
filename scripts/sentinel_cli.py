#!/usr/bin/env python3
"""
SentinelOS CLI Platform - Interactive AUV Operating System Demo & Monitoring
Provides an interactive terminal (REPL) to inject tasks, step the system,
monitor battery, and simulate connection loss to the AUV.
"""

import sys
import os
import argparse
import cmd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from sentinel_os.core.system_simulator import SystemSimulator
from sentinel_os.core.task import Task
import random

class SentinelTerminal(cmd.Cmd):
    intro = ""
    prompt = "[SentinelOS Connected] > "

    def __init__(self, simulator, console):
        super().__init__()
        self.sim = simulator
        self.console = console
        self.sim.initialize()
        self.manual_task_id = 9000
        self._update_prompt()
        
    def _update_prompt(self):
        if self.sim.disconnected:
            self.prompt = "[SentinelOS \033[91mDISCONNECTED\033[0m] > "
        else:
            self.prompt = "[SentinelOS \033[92mCONNECTED\033[0m] > "

    def do_status(self, arg):
        """Show current AUV status (Battery, Memory, Faults, Phase)"""
        table = Table(title="AUV System Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", justify="right")
        
        mem = self.sim.resource_manager.available_memory
        bat = self.sim.resource_manager.current_battery
        
        table.add_row("Time/Step", str(self.sim.time))
        table.add_row("Memory Level", f"{mem:.1f}%")
        table.add_row("Battery Level", f"{bat:.1f}%")
        table.add_row("Total Faults", str(len(self.sim.metrics.faults)))
        table.add_row("AI Interventions", str(self.sim.ai_advisor.advisor_interventions if self.sim.ai_advisor else 0))
        table.add_row("Connection Status", "DISCONNECTED" if self.sim.disconnected else "CONNECTED")
        
        self.console.print(table)

    def do_step(self, arg):
        """Run the simulation for N steps. Usage: step <n>"""
        try:
            steps = int(arg) if arg else 1
        except ValueError:
            self.console.print("[red]Invalid number of steps.[/red]")
            return
            
        for _ in range(steps):
            if self.sim.time >= self.sim.max_time:
                self.console.print("[red]Simulation maximum time reached.[/red]")
                break
                
            self._run_single_step()
            
        self.do_status("")

    def _run_single_step(self):
        # A simplified single step mirroring original logic
        # In disconnected mode, manual spawn disabled but task generator continues
        
        self.sim.event_manager.generate_events(self.sim.time)
        new_tasks = self.sim.task_generator.generate_task(self.sim.time)
        self.sim.kernel.add_tasks(new_tasks)
        
        # Disconnected AI emergency handling
        if self.sim.disconnected and self.sim.resource_manager.current_battery < 20.0:
            # Emergency shed some tasks
            pass
            
        sys_state = {"available_memory": self.sim.resource_manager.available_memory}
        task = self.sim.kernel.get_next_task(sys_state)
        
        if task:
            if not hasattr(task, "remaining_time"):
                task.remaining_time = random.randint(3, 8)
                
            if not self.sim.resource_manager.allocate(task):
                task.state = "WAITING"
            else:
                task.execute(2)
                task.remaining_time -= 2
                self.sim.resource_manager.consume_energy(task)
                
                faults = self.sim.faults_injector.inject_task_fault(task, self.sim.time)
                fault_occurred = len(faults) > 0
                
                # Report faults live
                for f in faults:
                    self.console.print(f"[bold red]❌ FAULT DURING STEP {self.sim.time}: {f['fault_type']} on Task {task.tid}[/bold red]")
                    self.sim.metrics.record_fault(f)
                    
                if task.deadline and self.sim.time > task.deadline and task.remaining_time > 0:
                    self.console.print(f"[bold yellow]⏰ DEADLINE MISSED: Task {task.tid}[/bold yellow]")
                    
                self.sim.resource_manager.release(task)
                
                if task.state == "FAULT":
                    if random.random() < 0.5:
                        task.state = "READY"
                        self.sim.kernel.requeue_task(task)
                elif task.remaining_time > 0:
                    self.sim.kernel.requeue_task(task)
        
        self.sim.metrics.record_step({"time": self.sim.time})
        self.sim.time += 1

    def do_spawn(self, arg):
        """Spawn a manual task. Usage: spawn <task_type> <priority:1-10> <is_critical:True/False>"""
        if self.sim.disconnected:
            self.console.print("[bold red]ERROR: Cannot inject tasks. AUV is Disconnected![/bold red]")
            return
            
        args = arg.split()
        if len(args) < 3:
            self.console.print("[yellow]Usage: spawn <task_type> <priority> <is_critical>[/yellow]")
            return
            
        task_type = args[0]
        try:
            priority = int(args[1])
            is_critical = args[2].lower() in ['true', '1', 't', 'y', 'yes']
        except ValueError:
            self.console.print("[red]Invalid priority or critical value.[/red]")
            return
            
        task = Task(
            tid=self.manual_task_id,
            task_type=task_type,
            base_priority=priority,
            deadline=self.sim.time + 30,
            critical=is_critical
        )
        self.manual_task_id += 1
        
        self.console.print(f"[blue]Analyzing manual sequence: {task_type}...[/blue]")
        
        if self.sim.ai_advisor:
            sys_state = {"available_memory": self.sim.resource_manager.available_memory}
            prob, risks = self.sim.ai_advisor.analyze_task_risk(task, sys_state)
            
            if prob > 0.5:
                self.console.print(Panel(
                    f"⚠️ [bold red]SYSTEM WARNING[/bold red] ⚠️\n"
                    f"Command has a {prob:.1%} chance of triggering a fault.\n"
                    f"Risk Factors: {', '.join(risks)}",
                    border_style="red"
                ))
                confirm = input("Override warning and proceed? (y/n): ")
                if confirm.lower() != 'y':
                    self.console.print("[yellow]Task injection cancelled.[/yellow]")
                    return
        
        self.sim.kernel.add_tasks([task])
        self.console.print(f"[bold green]Task {task.tid} injected into OS queues.[/bold green]")

    def do_disconnect(self, arg):
        """Simulate AUV connection loss (Disables remote commands)"""
        self.sim.disconnected = True
        self._update_prompt()
        self.console.print("[bold red]Connection lost. AUV switching to autonomous survival mode...[/bold red]")
        
    def do_reconnect(self, arg):
        """Simulate regaining connection to AUV"""
        self.sim.disconnected = False
        self._update_prompt()
        self.console.print("[bold green]Connection re-established. Remote telemetry active.[/bold green]")
        
    def do_quit(self, arg):
        """Exit the terminal"""
        self.console.print("Disconnecting from SentinelOS...")
        return True
        
    def do_EOF(self, arg):
        self.console.print()
        return self.do_quit(arg)


def main():
    parser = argparse.ArgumentParser(description="SentinelOS CLI Platform - Interactive AUV OS Demo")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive CLI mode")
    parser.add_argument("--baseline", "-b", action="store_true", help="Disable AI advisor for baseline comparison")
    parser.add_argument("--steps", "-n", type=int, default=500, help="Maximum simulation steps (default: 500)")
    
    args = parser.parse_args()
    
    console = Console()
    
    if args.interactive:
        console.print(Panel.fit(
            "🔷 SentinelOS AUV Terminal 🔷\n"
            "Interactive Shell for Remote OS Injection & Monitoring",
            border_style="blue"
        ))
        sim = SystemSimulator(enable_ai=not args.baseline, seed=42)
        sim.max_time = args.steps
        
        terminal = SentinelTerminal(sim, console)
        terminal.cmdloop()
    else:
        console.print("[red]❌ Use --interactive flag to run interactive mode.[/red]")
        console.print("   Type: python scripts/sentinel_cli.py --help for options.")


if __name__ == "__main__":
    main()
