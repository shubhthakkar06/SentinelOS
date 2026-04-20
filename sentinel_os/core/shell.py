"""
sentinel_os/core/shell.py
-------------------------
The interactive REPL for SentinelOS.
Provides a "real OS" interface with commands like ps, top, and hot-swap schedulers.
"""

import time
import os
import sys
import threading
from typing import Optional
from rich.console import Console, Group
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.align import Align
from rich.text import Text
from rich import box

from sentinel_os.core.system_simulator import SystemSimulator
from sentinel_os.core.task import TaskState


class SentinelShell:
    def __init__(self, simulator: SystemSimulator):
        self.sim = simulator
        self.console = Console()
        self.running = True
        self._auto_stepping = False

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def boot_sequence(self):
        """Realistic hardware boot sequence."""
        self.clear()
        
        # ASCII Logo
        logo = """
        [bold cyan]
         ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗     
        ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║     
        ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║     
        ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║     
        ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
        ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
        [/bold cyan]
        [bold white]  >> SECURE KERNEL v2.0 - AUV SUBMERSIBLE EDITION <<[/bold white]
        """
        self.console.print(Align.center(logo))
        time.sleep(0.5)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
            transient=True
        ) as progress:
            # Use explicit Task IDs to avoid indexing issues
            tasks = {
                "t1": progress.add_task("[yellow]Probing Hardware Sensors...", total=100),
                "t2": progress.add_task("[yellow]Initializing AI Neural Core...", total=100),
                "t3": progress.add_task("[yellow]Allocating Memory Banks...", total=100),
                "t4": progress.add_task("[yellow]Mounting Kernel Modules...", total=100),
            }

            # Safety watchdog to prevent literal infinite loops if rich state hits a snag
            watchdog = 0
            while not progress.finished and watchdog < 1000:
                watchdog += 1
                time.sleep(0.01)
                
                # Advance t1 always
                progress.update(tasks["t1"], advance=2)
                
                # Chain others based on previous task progress
                t1_prog = progress.tasks[0].completed
                if t1_prog > 30:
                    progress.update(tasks["t2"], advance=3)
                
                t2_prog = progress.tasks[1].completed
                if t2_prog > 40:
                    progress.update(tasks["t3"], advance=1.5)
                
                t3_prog = progress.tasks[2].completed
                if t3_prog > 20:
                    progress.update(tasks["t4"], advance=4)

        self.console.print("[bold green]✔ SYSTEM BOOT COMPLETE. KERNEL ONLINE.[/bold green]")
        time.sleep(0.8)
        self.clear()
        self.print_banner()

    def print_banner(self):
        self.console.print("[bold cyan]SentinelOS v2.0[/bold cyan] | Kernel: [bold white]Active[/bold white] | User: [bold green]sentinel[/bold green]")
        self.console.print("[dim]Type 'help' for commands, 'top' for dashboard, 'run' for live operation.[/dim]")
        self.console.print("-" * 70)

    def run(self):
        self.boot_sequence()
        self.sim.initialize()

        while self.running:
            try:
                # Protected status generation to prevent infinite restart loops on error
                try:
                    status = self._get_prompt_status()
                    prompt_str = f"{status}\n[bold green]sentinel@auv[/bold green]:[blue]~$[/blue] "
                except Exception as e:
                    # Debug: Show error type to identify missing keys/atts
                    prompt_str = f"[bold red]!! STATS_BUS_FAILURE ({type(e).__name__}) !![/bold red]\n[bold green]sentinel@auv[/bold green]:[blue]~$[/blue] "
                
                cmd_line = Prompt.ask(prompt_str)
                
                if not cmd_line:
                    continue
                
                parts = cmd_line.strip().split()
                cmd = parts[0].lower()
                args = parts[1:]

                self.execute_command(cmd, args)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type 'shutdown' to exit cleanly.[/yellow]")
            except Exception as e:
                self.console.print(f"[red]CRITICAL KERNEL ERROR:[/red] {str(e)}")
                time.sleep(1) # Cooldown to prevent flooding on infinite loop errors

    def _get_prompt_status(self) -> str:
        stats = self.sim.resource_manager.stats()
        batt = int(stats['battery_fraction'] * 100)
        batt_color = "green" if batt > 50 else "yellow" if batt > 20 else "red"
        
        mem_load = stats['memory_utilization'] * 100
        mem_color = "green" if mem_load < 60 else "yellow" if mem_load < 85 else "red"
        
        sched_name = (self.sim.metrics.scheduler_name or "unknown").upper()
        mode_name = stats.get("mission_mode", "Connected").upper()
        mode_color = "green" if mode_name == "CONNECTED" else "bold red"
        
        status = (
            f"[dim]───[[/dim][{batt_color}]PWR: {batt}%[/{batt_color}][dim]]───"
            f"[[/dim][{mem_color}]MEM: {stats['memory_pressure']}[/{mem_color}][dim]]───"
            f"[[/dim][cyan]SCHED: {sched_name}[/cyan][dim]]───"
            f"[[/dim][{mode_color}]MODE: {mode_name}[/{mode_color}][dim]]───[/dim]"
        )
        return status

    def execute_command(self, cmd: str, args: list):
        # Command map for cleaner dispatch
        commands = {
            "help": self.cmd_help,
            "ps": self.cmd_ps,
            "ls": self.cmd_ps,
            "top": self.cmd_top,
            "step": lambda: self.cmd_step(args),
            "run": self.cmd_run_loop,
            "sysinfo": self.cmd_sysinfo,
            "info": self.cmd_sysinfo,
            "sched": lambda: self.cmd_sched(args),
            "clear": self.cmd_clear,
            "audit": self.cmd_audit,
            "log": self.cmd_audit,
            "mission": lambda: self.cmd_mission(args),
            "boot": self.boot_sequence,
            "shutdown": self.cmd_shutdown,
            "exit": self.cmd_shutdown
        }
        
        handler = commands.get(cmd)
        if handler:
            handler()
        else:
            self.console.print(f"[red]Unknown command:[/red] {cmd}. Type 'help' for assistance.")

    # ------------------------------------------------------------------ #
    #  Command Implementations                                           #
    # ------------------------------------------------------------------ #

    def cmd_help(self):
        table = Table(title="[bold cyan]SentinelOS Control Manual[/bold cyan]", box=box.ROUNDED, border_style="cyan")
        table.add_column("Command", style="bold yellow")
        table.add_column("Usage & Description", style="italic white")
        
        table.add_row("run", "Live mode: OS ticks automatically (Press Ctrl+C to stop)")
        table.add_row("step [n]", "Kernel Step: Advance simulation by N ticks")
        table.add_row("top", "Dashboard: Live resource/process monitor (HTOP-style)")
        table.add_row("ps", "Proc List: Detailed view of all system tasks")
        table.add_row("audit", "Audit Log: Live scroll of kernel events and AI alerts")
        table.add_row("sched [p]", "Hot-Swap: Change policy (hybrid, edf, priority, rr)")
        table.add_row("sysinfo", "Telemetry: Deep dive into AUV health and KPIs")
        table.add_row("boot", "Cold Reset: Reboot the SentinelOS kernel")
        table.add_row("mission [m]", "Switch mode: connect (Normal) / survive (Deep-sea stress)")
        table.add_row("clear", "Terminal Refresh")
        table.add_row("shutdown", "Power Off")
        
        self.console.print(table)

    def cmd_clear(self):
        self.clear()
        self.print_banner()

    def cmd_shutdown(self):
        self.running = False
        self.console.print("[bold red]SYSTEM POWERING DOWN...[/bold red]")
        time.sleep(0.5)

    def cmd_step(self, args):
        n = 1
        if args:
            try: n = int(args[0])
            except: pass
        
        self.sim.logger.mute()
        with Progress(SpinnerColumn(), TextColumn("[bold blue]Stepping Kernel..."), console=self.console, transient=True) as progress:
            progress.add_task("", total=n)
            for _ in range(n):
                self.sim.step()
        self.sim.logger.unmute()
        self.console.print(f"[dim]Kernel advanced to T={self.sim.time}[/dim]")

    def cmd_run_loop(self):
        """Auto-stepping mode with a clean live status dashboard. Ghost Mode enabled."""
        self.console.print("[bold yellow]Kernel Live Mode Active. (Ghost Mode: Stdout Muted)[/bold yellow]")
        self.sim.logger.mute()
        try:
            with Live(self._generate_run_dashboard(), refresh_per_second=5, screen=True) as live:
                while True:
                    self.sim.step()
                    live.update(self._generate_run_dashboard())
                    time.sleep(0.1)
        except KeyboardInterrupt:
            self.sim.logger.unmute()
            self.console.print("\n[bold green]Kernel PAUSED.[/bold green]")
        finally:
            self.sim.logger.unmute()

    def _generate_run_dashboard(self) -> Layout:
        stats = self.sim.resource_manager.stats()
        metrics = self.sim.metrics.to_dict()
        logs = self.sim.logger.get_recent_logs(8)
        
        log_text = Text()
        for log in logs:
            log_text.append(log + "\n", style="dim")
        
        # Dashboard header
        header = Panel(
            f"Sys Time: [bold]{self.sim.time}[/bold] | "
            f"PWR: [green]{stats['battery_fraction']*100:.1f}%[/green] | "
            f"RAM: [blue]{stats['memory_utilization']*100:.1f}%[/blue] | "
            f"Policy: [cyan]{self.sim.metrics.scheduler_name.upper()}[/cyan]",
            title="SentinelOS Heartbeat", border_style="yellow"
        )
        
        layout = Layout()
        layout.split(
            Layout(header, size=3),
            Layout(Panel(log_text, title="Internal Audit Stream", box=box.SIMPLE_HEAD), name="logs")
        )
        return layout

    def cmd_audit(self):
        """Live log audit screen that updates in-place and silences the main terminal."""
        self.console.print("[bold cyan]Entering Ghost Mode Audit Stream. Press Ctrl+C to exit.[/bold cyan]")
        self.sim.logger.mute()
        try:
            with Live(self._generate_log_panel(), refresh_per_second=4, screen=True) as live:
                while True:
                    self.sim.step() # Advance kernel to generate logs
                    live.update(self._generate_log_panel())
                    time.sleep(0.25)
        except KeyboardInterrupt:
            self.sim.logger.unmute()
        finally:
            self.sim.logger.unmute()
            self.console.print("\n[dim]Audit stream closed.[/dim]")

    def _generate_log_panel(self) -> Panel:
        logs = self.sim.logger.get_recent_logs(15) # Shorter for live view
        log_text = Text()
        for log in logs:
            if "[ERROR]" in log or "Fault" in log or "MISSED" in log:
                log_text.append(log + "\n", style="bold red")
            elif "[WARNING]" in log or "AI ADVISOR" in log:
                log_text.append(log + "\n", style="yellow")
            elif "COMPLETED" in log:
                log_text.append(log + "\n", style="green")
            else:
                log_text.append(log + "\n", style="dim")
        
        return Panel(log_text, title="Kernel Audit Trail", border_style="cyan", subtitle="Real-time Telemetry")

    def cmd_top(self):
        """High-fidelity HTOP-style dashboard. Mutes kernel noise."""
        self.clear()
        self.sim.logger.mute()
        try:
            with Live(self._generate_htop_layout(), refresh_per_second=2, screen=True) as live:
                while True:
                    self.sim.step()
                    live.update(self._generate_htop_layout())
                    time.sleep(0.3)
        except KeyboardInterrupt:
            self.sim.logger.unmute()
            self.clear()
            self.print_banner()
        finally:
            self.sim.logger.unmute()

    def _generate_htop_layout(self) -> Layout:
        stats = self.sim.resource_manager.stats()
        tasks = self.sim.kernel.scheduler.get_queued_tasks()
        
        # 1. Resource Gauges (Top Row)
        # Memory Bar
        mem_used = stats['total_memory'] - stats['available_memory']
        mem_pct = stats['memory_utilization'] * 100
        mem_bar = Progress(BarColumn(bar_width=None), TextColumn("{task.percentage:>3.0f}%"))
        mem_task = mem_bar.add_task("", total=100, completed=mem_pct)
        
        # Battery Bar
        batt_pct = stats['battery_fraction'] * 100
        batt_bar = Progress(BarColumn(bar_width=None), TextColumn("{task.percentage:>3.0f}%"))
        batt_task = batt_bar.add_task("", total=100, completed=batt_pct)

        header_table = Table.grid(expand=True)
        header_table.add_column(ratio=1)
        header_table.add_column(ratio=1)
        header_table.add_row(
            Panel(Group(f"Memory: {mem_used}/{stats['total_memory']} units", mem_bar), title="RAM Usage", border_style="blue"),
            Panel(Group(f"Battery: {stats['current_battery']:.1f}/{stats['total_battery']} units", batt_bar), title="Power", border_style="green")
        )

        # 2. Process Table
        proc_table = Table(expand=True, box=box.SIMPLE_HEAD)
        proc_table.add_column("TID", style="dim", width=4)
        proc_table.add_column("TYPE", style="bold cyan")
        proc_table.add_column("PRIO", justify="right")
        proc_table.add_column("EFF", style="bold magenta", justify="right")
        proc_table.add_column("STATE", justify="center")
        proc_table.add_column("DEADLINE", style="yellow", justify="right")
        proc_table.add_column("PROGRESS")

        for t in tasks[:15]:
            # Color state
            state_str = str(t.state.value if hasattr(t.state, 'value') else t.state)
            if state_str == "BLOCKED" and t.blocked_reason:
                state_label = f"BLOCKED ({t.blocked_reason})"
            else:
                state_label = state_str
                
            state_style = "green" if state_str == "RUNNING" else "blue" if state_str == "READY" else "red" if state_str == "BLOCKED" else "yellow"
            
            # AI Boost indicator
            prio_eff = str(t.effective_priority)
            if t.ai_boost > 0:
                prio_eff = f"[bold magenta]{prio_eff} ⚡[/bold magenta]"

            # Progress bar
            prog_val = ((t.burst_time - t.remaining_time) / t.burst_time) * 100
            prog_bar = Progress(BarColumn(bar_width=10), console=self.console)
            prog_bar.add_task("", total=100, completed=prog_val)

            proc_table.add_row(
                str(t.tid),
                t.task_type,
                str(t.base_priority),
                prio_eff,
                f"[{state_style}]{state_label}[/{state_style}]",
                str(t.deadline) if t.deadline else "-",
                prog_bar
            )

        # 3. Mini KPI Panel
        metrics = self.sim.metrics.to_dict()
        kpi_text = (
            f"Sys Time: [bold]{self.sim.time}[/bold] | "
            f"Scheduler: [bold yellow]{self.sim.metrics.scheduler_name.upper()}[/bold yellow] | "
            f"Cmpl Rate: [green]{metrics['task_completion_rate']*100:.1f}%[/green] | "
            f"Miss Rate: [red]{metrics['deadline_miss_rate']*100:.1f}%[/red]"
        )

        layout = Layout()
        layout.split(
            Layout(header_table, name="header", size=5),
            Layout(Panel(proc_table, title="Kernel Process Monitor", border_style="white"), name="body"),
            Layout(Panel(kpi_text, box=box.MINIMAL), name="footer", size=3)
        )
        return layout

    def cmd_ps(self):
        """Live-updating process list with autonomous kernel stepping."""
        self.console.print("[bold cyan]Opening Process Monitor (Ghost Mode).[/bold cyan]")
        self.sim.logger.mute()
        try:
            with Live(self._generate_ps_table(), refresh_per_second=4, screen=True) as live:
                while True:
                    self.sim.step() # Tick the kernel so tasks move!
                    live.update(self._generate_ps_table())
                    time.sleep(0.25)
        except KeyboardInterrupt:
            self.sim.logger.unmute()
        finally:
            self.sim.logger.unmute()

    def _generate_ps_table(self) -> Panel:
        tasks = self.sim.kernel.scheduler.get_queued_tasks()
        proc_table = Table(expand=True, box=box.SIMPLE_HEAD)
        proc_table.add_column("TID", style="dim", width=4)
        proc_table.add_column("TYPE", style="bold cyan")
        proc_table.add_column("PRIO", justify="right")
        proc_table.add_column("EFF", style="bold magenta", justify="right")
        proc_table.add_column("STATE", justify="center")
        proc_table.add_column("PROGRESS")

        for t in tasks[:15]:
            state_str = str(t.state.value if hasattr(t.state, 'value') else t.state)
            if state_str == "BLOCKED" and t.blocked_reason:
                state_label = f"BLOCKED ({t.blocked_reason})"
            else:
                state_label = state_str
                
            state_style = "green" if state_str == "RUNNING" else "blue" if state_str == "READY" else "red" if state_str == "BLOCKED" else "yellow"
            
            prio_eff = str(t.effective_priority)
            if t.ai_boost > 0:
                prio_eff = f"[magenta]{prio_eff} ⚡[/magenta]"

            prog_val = ((t.burst_time - t.remaining_time) / t.burst_time) * 100
            prog_bar = Progress(BarColumn(bar_width=10))
            prog_bar.add_task("", total=100, completed=prog_val)

            proc_table.add_row(
                str(t.tid), t.task_type, str(t.base_priority), prio_eff,
                f"[{state_style}]{state_label}[/{state_style}]", prog_bar
            )
        
        return Panel(proc_table, title="Active Kernel Threads", border_style="white")

    def cmd_sysinfo(self):
        stats = self.sim.resource_manager.stats()
        metrics = self.sim.get_results()
        
        grid = Table.grid(expand=True, padding=1)
        grid.add_column()
        grid.add_column()
        
        grid.add_row(
            Panel(f"[bold cyan]Telemetery Statistics[/bold cyan]\n"
                  f"Uptime: {self.sim.time} ticks\n"
                  f"Peak RAM: {stats['peak_memory_usage']} units\n"
                  f"Alloc Failures: {stats['alloc_failures']}\n"
                  f"Energy Spent: {stats['total_energy_consumed']} units",
                  title="Hardware Health", border_style="blue"),
            Panel(f"Tasks Completed: {metrics['tasks_completed']}\n"
                  f"Throughput: {metrics['throughput']:.3f} tps\n"
                  f"Context Switches: {metrics['context_switches']}\n"
                  f"Avg Waiting: {metrics['average_waiting_time']:.1f} ticks",
                  title="Scheduler Efficiency", border_style="magenta")
        )
        
        self.console.print(grid)

    def cmd_sched(self, args):
        if not args:
            self.console.print(f"Current Policy: [bold yellow]{self.sim.metrics.scheduler_name.upper()}[/bold yellow]")
            return
        policy = args[0].lower()
        if policy in ("hybrid", "edf", "priority", "rr"):
            self.sim.set_scheduler(policy)
            self.console.print(f"[bold green]Kernel re-scheduled via {policy.upper()}[/bold green]")
        else:
            self.console.print(f"[red]Error:[/red] Unknown policy '{policy}'")

    def cmd_mission(self, args):
        if not args:
            mode = self.sim.resource_manager.mission_mode
            self.console.print(f"Current Mission State: [bold cyan]{mode}[/bold cyan]")
            return
        
        mode = args[0].lower()
        if mode in ("connect", "connected", "human"):
            self.sim.resource_manager.trigger_connected()
            self.console.print("[bold green]Link Established. Hardware resources restored to nominal levels.[/bold green]")
        elif mode in ("survive", "survival", "autonomous"):
            self.sim.resource_manager.trigger_survival()
            self.console.print("[bold red]CRITICAL: LOST LINK. Switching to Autonomous Survival Mode.[/bold red]")
            self.console.print("[dim]Battery drained to core reserves. Memory pressure high. Fault risks elevated.[/dim]")
        else:
            self.console.print(f"[red]Error:[/red] Unknown mission mode '{mode}'")

    def cmd_boot(self):
        self.boot_sequence()

