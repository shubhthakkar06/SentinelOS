"""
sentinel_os/core/shell.py
-------------------------
The interactive REPL for SentinelOS AUV.
Provides a realistic submarine operating system interface with 25+ commands.

Commands cover: process management, navigation, battery management,
sonar, communications, hull monitoring, and survival operations.
"""

import time
import os
import sys
import random
import datetime
import json
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
from rich.columns import Columns
from rich import box

from sentinel_os.core.system_simulator import SystemSimulator
from sentinel_os.core.task import TaskState

# AI Command Imports
from sentinel_os.shell.commands.advisory_cmd import cmd_advisory
from sentinel_os.shell.commands.predict_cmd import cmd_predict
from sentinel_os.shell.commands.prioritize_cmd import cmd_prioritize
from sentinel_os.shell.commands.compare_cmd import cmd_compare


class SentinelShell:
    def __init__(self, simulator: SystemSimulator):
        self.sim = simulator
        self.console = Console()
        self.running = True
        self._auto_stepping = False
        self._boot_time = datetime.datetime.now()
        self._operator = "CDR.SENTINEL"
        self._mission_id = f"SM-{random.randint(1000,9999)}"

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def boot_sequence(self):
        """Realistic AUV boot sequence."""
        self.clear()

        logo = """
        [bold cyan]
         ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗     
        ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║     
        ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║     
        ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║     
        ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
        ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
        [/bold cyan]
        [bold white]  >> AUTONOMOUS UNDERWATER VEHICLE KERNEL v3.0 <<[/bold white]
        [dim]  Mission ID: {mid}  |  Classification: RESTRICTED[/dim]
        
        [italic yellow]NOTE: Hardware interfaces are simulated OS service layers.[/italic yellow]
        [italic yellow]      Physical actuators/sensors are abstracted as kernel processes.[/italic yellow]
        """.format(mid=self._mission_id)
        self.console.print(Align.center(logo))
        time.sleep(0.5)

        # Boot phases
        boot_phases = [
            ("Initializing Kernel Subsystems", [
                "[yellow]Loading microkernel modules...",
                "[yellow]Initializing process scheduler...",
                "[yellow]Allocating memory banks (100 units)...",
            ]),
            ("Hardware Diagnostics", [
                "[yellow]Probing thruster array (4 units)...",
                "[yellow]Sonar transducer self-test...",
                "[yellow]Hydrophone array calibration...",
                "[yellow]Hull pressure sensors OK...",
            ]),
            ("Battery Management System", [
                "[yellow]BMS init: 8 cells detected (2S4P)...",
                "[yellow]Cell voltage check: all nominal...",
                "[yellow]Thermal sensors: 22°C average...",
                "[yellow]Pack SOC: 100%  |  Voltage: 8.40V...",
            ]),
            ("Navigation & Comms", [
                "[yellow]INS alignment...",
                "[yellow]GPS fix acquired (surface)...",
                "[yellow]Encrypted comms link: ONLINE...",
                "[yellow]AI Neural Core: LOADED...",
            ]),
            ("AI Advisory Core", [
                "[yellow]Loading RandomForest model...",
                "[yellow]Training corpus: 1,200 AUV telemetry samples...",
                f"[yellow]Accuracy: {self.sim.ai_advisor.accuracy:.1%}  |  Precision: {self.sim.ai_advisor.precision:.1%}...",
                "[yellow]Fault thresholds: LOW < 0.4 | MEDIUM < 0.7 | HIGH ≥ 0.7...",
            ]),
        ]

        for phase_name, items in boot_phases:
            self.console.print(f"\n[bold white]── {phase_name} ──[/bold white]")
            for item in items:
                self.console.print(f"  {item}")
                time.sleep(0.08)
            self.console.print(f"  [green]✔ {phase_name} complete[/green]")
            time.sleep(0.1)

        self.console.print(f"\n[bold green]✔ ALL SYSTEMS NOMINAL. KERNEL ONLINE.[/bold green]")
        self.console.print(f"[dim]  Operator: {self._operator}  |  Uplink: ACTIVE  |  Ready for orders.[/dim]\n")
        time.sleep(0.5)
        self.clear()
        self.print_banner()

    def print_banner(self):
        self.console.print(f"[bold cyan]SentinelOS v3.0[/bold cyan] | AUV Kernel: [bold green]ONLINE[/bold green] | Mission: [bold yellow]{self._mission_id}[/bold yellow] | Operator: [bold white]{self._operator}[/bold white]")
        self.console.print("[dim]Type 'help' for command reference. 'top' for live dashboard. 'run' for autonomous mode.[/dim]")
        self.console.print("─" * 80)

    def run(self):
        self.boot_sequence()
        self.sim.initialize()

        while self.running:
            try:
                try:
                    status = self._get_prompt_status()
                    prompt_str = f"{status}\n[bold green]sentinel@auv[/bold green]:[bold blue]~$[/bold blue] "
                except Exception as e:
                    prompt_str = f"[bold red]!! SENSOR_BUS_FAILURE ({type(e).__name__}) !![/bold red]\n[bold green]sentinel@auv[/bold green]:[blue]~$[/blue] "

                cmd_line = Prompt.ask(prompt_str)

                if not cmd_line:
                    continue

                parts = cmd_line.strip().split()
                cmd = parts[0].lower()
                args = parts[1:]

                self.execute_command(cmd, args)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type 'shutdown' to power off or 'emergency' for emergency protocol.[/yellow]")
            except Exception as e:
                self.console.print(f"[red]KERNEL PANIC:[/red] {str(e)}")
                time.sleep(0.5)

    def _get_prompt_status(self) -> str:
        stats = self.sim.resource_manager.stats()
        env = self.sim.environment

        batt = int(stats['battery_soc'])
        batt_color = "green" if batt > 50 else "yellow" if batt > 20 else "bold red"

        mem_load = stats['memory_utilization'] * 100
        mem_color = "green" if mem_load < 60 else "yellow" if mem_load < 85 else "red"

        depth = env.depth
        depth_color = "cyan" if depth < 100 else "yellow" if depth < 300 else "bold red"

        sched_name = (self.sim.metrics.scheduler_name or "unknown").upper()
        mode_name = stats.get("mission_mode", "Connected").upper()
        mode_color = "green" if mode_name == "CONNECTED" else "bold red"

        phase = stats.get("survival_phase", 0)
        phase_str = f" P{phase}" if phase > 0 else ""

        charge = stats.get("charge_state", "NOMINAL")

        status = (
            f"[dim]───[[/dim][{batt_color}]PWR:{batt}% {charge}[/{batt_color}][dim]]───"
            f"[[/dim][{depth_color}]DEPTH:{depth:.0f}m[/{depth_color}][dim]]───"
            f"[[/dim][cyan]HDG:{env.heading:.0f}°{env.compass_bearing}[/cyan][dim]]───"
            f"[[/dim][{mem_color}]MEM:{stats['memory_pressure']}[/{mem_color}][dim]]───"
            f"[[/dim][cyan]SCHED:{sched_name}[/cyan][dim]]───"
            f"[[/dim][{mode_color}]MODE:{mode_name}{phase_str}[/{mode_color}][dim]]───[/dim]"
        )
        return status

    def execute_command(self, cmd: str, args: list):
        commands = {
            # Process management
            "help": self.cmd_help,
            "ps": self.cmd_ps,
            "top": self.cmd_top,
            "kill": lambda: self.cmd_kill(args),
            "suspend": lambda: self.cmd_suspend(args),
            "resume": lambda: self.cmd_resume(args),
            "nice": lambda: self.cmd_nice(args),

            # Kernel operations
            "step": lambda: self.cmd_step(args),
            "run": self.cmd_run_loop,
            "sched": lambda: self.cmd_sched(args),
            "mission": lambda: self.cmd_mission(args),

            # Navigation & vehicle
            "dive": lambda: self.cmd_dive(args),
            "surface": self.cmd_surface,
            "heading": lambda: self.cmd_heading(args),
            "throttle": lambda: self.cmd_throttle(args),
            "ballast": lambda: self.cmd_ballast(args),
            "nav": self.cmd_nav,

            # Sensors & comms
            "sonar": lambda: self.cmd_sonar(args),
            "hydrophone": self.cmd_hydrophone,
            "sensors": self.cmd_sensors,
            "comms": lambda: self.cmd_comms(args),
            "hull": self.cmd_hull,
            "ping": lambda: self.cmd_ping(args),

            # Battery & system
            "battery": self.cmd_battery,
            "sysinfo": self.cmd_sysinfo,
            "info": self.cmd_sysinfo,
            "uptime": self.cmd_uptime,
            "free": self.cmd_free,
            "df": self.cmd_df,
            "who": self.cmd_who,
            "dmesg": self.cmd_dmesg,

            # Logs & audit
            "audit": self.cmd_audit,
            "log": self.cmd_audit,
            "blackbox": self.cmd_blackbox,

            # AI Advisory
            "advisory": self.cmd_advisory_wrap,
            "predict": self.cmd_predict_wrap,
            "prioritize": self.cmd_prioritize_wrap,
            "compare": self.cmd_compare_wrap,
            "fault": lambda: self.cmd_fault(args),

            # Emergency
            "emergency": self.cmd_emergency,

            # System
            "clear": self.cmd_clear,
            "boot": self.boot_sequence,
            "shutdown": self.cmd_shutdown,
            "exit": self.cmd_shutdown,
        }

        handler = commands.get(cmd)
        if handler:
            handler()
        else:
            self.console.print(f"[red]sentinel: command not found:[/red] {cmd}. Type 'help' for available commands.")

    # ════════════════════════════════════════════════════════════════════
    #  HELP
    # ════════════════════════════════════════════════════════════════════

    def cmd_help(self):
        sections = [
            ("Process Management", [
                ("ps", "Process list — live view of all kernel threads"),
                ("top", "Dashboard — HTOP-style live system monitor"),
                ("kill <tid>", "Terminate a process by TID"),
                ("suspend <tid>", "Suspend (freeze) a process"),
                ("resume <tid>", "Resume a suspended process"),
                ("nice <tid> <prio>", "Change process priority (1-10)"),
            ]),
            ("Kernel Operations", [
                ("run", "Autonomous mode — kernel ticks automatically"),
                ("step [n]", "Manual step — advance kernel by N ticks"),
                ("sched [policy]", "Hot-swap scheduler (hybrid/edf/priority/rr)"),
                ("mission [mode]", "Switch mode: connect | survive"),
            ]),
            ("Navigation & Vehicle", [
                ("dive <depth>", "Set depth target — DepthControl service"),
                ("surface", "Trigger surface protocol — OS emergency handler"),
                ("heading <deg>", "Set heading — Navigation service parameter"),
                ("throttle <0-100>", "Set thruster allocation — ResourceManager"),
                ("ballast <flood|blow|status>", "Ballast state — simulated actuator service"),
                ("nav", "Navigation computer — full status display"),
            ]),
            ("Sensors & Comms", [
                ("sonar <active|passive|off>", "Sonar process mode — sensor service"),
                ("hydrophone", "Hydrophone process — passive listener service"),
                ("sensors", "All sensor readings dashboard"),
                ("comms [send|status]", "Communications system"),
                ("hull", "Hull integrity & pressure monitor"),
                ("ping [target]", "Network connectivity test"),
            ]),
            ("Battery & System", [
                ("battery", "Battery Management System — per-cell status"),
                ("sysinfo", "Telemetry — deep system health & KPIs"),
                ("uptime", "System uptime and load averages"),
                ("free", "Memory usage summary"),
                ("df", "Storage utilization"),
                ("who", "Connected operators"),
                ("dmesg", "Kernel message buffer (full log)"),
            ]),
            ("Mission", [
                ("audit", "Live kernel event stream"),
                ("blackbox", "Export mission telemetry to file"),
                ("emergency", "EMERGENCY protocol — surface + distress"),
            ]),
            ("AI Advisory", [
                ("predict", "Fault risk assessment — all services (Module 1)"),
                ("prioritize", "AI priority recommendations (Module 2)"),
                ("advisory", "Combined fault + priority report"),
                ("compare", "Benchmark all schedulers (AI vs baseline)"),
                ("fault inject <svc>", "Inject fault into a service (testing)"),
            ]),
            ("System", [
                ("clear", "Clear terminal"),
                ("shutdown", "Power off AUV systems"),
            ]),
        ]

        self.console.print()
        self.console.print(Panel(
            f"[bold]SentinelOS AUV Command Reference[/bold]\n[dim]Mission {self._mission_id} | Kernel v3.0[/dim]",
            border_style="cyan",
            box=box.DOUBLE,
        ))

        for section_name, cmds in sections:
            table = Table(box=box.SIMPLE_HEAD, expand=True, border_style="dim")
            table.add_column("Command", style="bold yellow", width=25)
            table.add_column("Description", style="white")
            for cmd, desc in cmds:
                table.add_row(cmd, desc)
            self.console.print(Panel(table, title=f"[bold cyan]{section_name}[/bold cyan]", border_style="dim", box=box.ROUNDED))

    # ════════════════════════════════════════════════════════════════════
    #  PROCESS MANAGEMENT
    # ════════════════════════════════════════════════════════════════════

    def cmd_kill(self, args):
        if not args:
            self.console.print("[red]Usage: kill <tid>[/red]")
            return
        try:
            tid = int(args[0])
            result = self.sim.kill_task(tid)
            self.console.print(f"[yellow]{result}[/yellow]")
        except ValueError:
            self.console.print("[red]Error: TID must be a number[/red]")

    def cmd_suspend(self, args):
        if not args:
            self.console.print("[red]Usage: suspend <tid>[/red]")
            return
        try:
            tid = int(args[0])
            result = self.sim.suspend_task(tid)
            self.console.print(f"[yellow]{result}[/yellow]")
        except ValueError:
            self.console.print("[red]Error: TID must be a number[/red]")

    def cmd_resume(self, args):
        if not args:
            self.console.print("[red]Usage: resume <tid>[/red]")
            return
        try:
            tid = int(args[0])
            result = self.sim.resume_task(tid)
            self.console.print(f"[green]{result}[/green]")
        except ValueError:
            self.console.print("[red]Error: TID must be a number[/red]")

    def cmd_nice(self, args):
        if len(args) < 2:
            self.console.print("[red]Usage: nice <tid> <priority>[/red]")
            return
        try:
            tid = int(args[0])
            prio = int(args[1])
            result = self.sim.nice_task(tid, prio)
            self.console.print(f"[cyan]{result}[/cyan]")
        except ValueError:
            self.console.print("[red]Error: TID and priority must be numbers[/red]")

    # ════════════════════════════════════════════════════════════════════
    #  KERNEL OPERATIONS
    # ════════════════════════════════════════════════════════════════════

    def cmd_clear(self):
        self.clear()
        self.print_banner()

    def cmd_shutdown(self):
        self.running = False
        shutdown_msg = (
            "  ╔═══════════════════════════════════════╗\n"
            "  ║    SYSTEM SHUTDOWN INITIATED          ║\n"
            "  ║    Flushing blackbox recorder...      ║\n"
            "  ║    Releasing all process memory...    ║\n"
            "  ║    Disabling thrusters...             ║\n"
            "  ║    Ballast tanks: NEUTRAL             ║\n"
            "  ║    Distress beacon: STANDBY           ║\n"
            "  ║    POWER OFF                          ║\n"
            "  ╚═══════════════════════════════════════╝"
        )
        self.console.print(Panel(shutdown_msg, style="bold red", border_style="bold red", box=box.HEAVY))
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
        self.console.print(f"[dim]Kernel advanced to T={self.sim.time} | Depth: {self.sim.environment.depth:.0f}m | Battery: {self.sim.resource_manager.bms.pack_soc:.0f}%[/dim]")

    def cmd_run_loop(self):
        """Auto-stepping mode with live dashboard."""
        self.console.print("[bold yellow]Kernel Live Mode Active. Press Ctrl+C to pause.[/bold yellow]")
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
        env = self.sim.environment
        logs = self.sim.logger.get_recent_logs(10)

        log_text = Text()
        for log in logs:
            if "[ERROR]" in log or "Fault" in log or "FAILED" in log:
                log_text.append(log + "\n", style="bold red")
            elif "[WARNING]" in log or "PHASE" in log:
                log_text.append(log + "\n", style="yellow")
            elif "COMPLETED" in log:
                log_text.append(log + "\n", style="green")
            elif "suspended" in log.lower():
                log_text.append(log + "\n", style="magenta")
            else:
                log_text.append(log + "\n", style="dim")

        # Header
        batt_color = "green" if stats['battery_soc'] > 50 else "yellow" if stats['battery_soc'] > 20 else "red"
        depth_color = "cyan" if env.depth < 200 else "yellow" if env.depth < 400 else "red"
        mode_color = "green" if stats['mission_mode'] == "Connected" else "red"
        phase_str = f" Phase {stats['survival_phase']}" if stats['survival_phase'] > 0 else ""

        header = Panel(
            f"T=[bold]{self.sim.time}[/bold] │ "
            f"[{batt_color}]PWR:{stats['battery_soc']:.0f}% {stats['charge_state']}[/{batt_color}] │ "
            f"[{depth_color}]DEPTH:{env.depth:.0f}m[/{depth_color}] │ "
            f"HDG:{env.heading:.0f}°{env.compass_bearing} │ "
            f"SPD:{env.speed:.1f}kt │ "
            f"MEM:{stats['memory_pressure']} │ "
            f"[cyan]SCHED:{self.sim.metrics.scheduler_name.upper()}[/cyan] │ "
            f"[{mode_color}]{stats['mission_mode'].upper()}{phase_str}[/{mode_color}]",
            title="[bold]SentinelOS AUV Heartbeat[/bold]", border_style="yellow", box=box.HEAVY
        )

        # Process summary
        tasks = self.sim.kernel.scheduler.get_queued_tasks()
        state_counts = {}
        for t in tasks:
            # UI Fix: Count the last active task as RUNNING for the summary line
            is_active = (t == self.sim.prev_task and t.state != TaskState.TERMINATED)
            s = "RUNNING" if is_active else t.state.value
            state_counts[s] = state_counts.get(s, 0) + 1

        state_line = " │ ".join(
            f"[{self._state_color(s)}]{s}:{c}[/{self._state_color(s)}]"
            for s, c in sorted(state_counts.items())
        )
        proc_summary = Panel(
            f"Threads: {len(tasks)} │ {state_line}",
            title="Process States", border_style="blue", box=box.SIMPLE
        )

        layout = Layout()
        layout.split(
            Layout(header, size=3),
            Layout(proc_summary, size=3),
            Layout(Panel(log_text, title="Kernel Audit Stream", box=box.SIMPLE_HEAD), name="logs")
        )
        return layout

    # ════════════════════════════════════════════════════════════════════
    #  NAVIGATION & VEHICLE
    # ════════════════════════════════════════════════════════════════════

    def cmd_dive(self, args):
        if not args:
            self.console.print(f"[cyan]Current depth: {self.sim.environment.depth:.1f}m | Target: {self.sim.environment.target_depth:.1f}m[/cyan]")
            return
        try:
            target = float(args[0])
            if target > self.sim.environment.max_rated_depth:
                self.console.print(f"[bold red]WARNING: Target {target}m exceeds max rated depth ({self.sim.environment.max_rated_depth}m)![/bold red]")
                self.console.print("[yellow]Proceeding with caution — hull stress will increase.[/yellow]")
            self.sim.environment.set_dive(target)
            self.console.print(f"[cyan]DIVE ORDER: Descending to {target:.0f}m. Ballast flooding.[/cyan]")
            self.console.print(f"[dim]  Current: {self.sim.environment.depth:.0f}m → Target: {target:.0f}m[/dim]")
        except ValueError:
            self.console.print("[red]Usage: dive <depth_meters>[/red]")

    def cmd_surface(self):
        self.sim.environment.set_surface()
        self.sim.environment.set_throttle(min(100, self.sim.environment.throttle + 30))
        
        emergency_msg = (
            "  ╔══════════════════════════════════════╗\n"
            "  ║   EMERGENCY SURFACE INITIATED       ║\n"
            "  ║   Ballast tanks: FULL BLOW           ║\n"
            "  ║   Thrusters: MAX ASCENT              ║\n"
            "  ║   Non-critical processes: SUSPENDED  ║\n"
            "  ╚══════════════════════════════════════╝"
        )
        self.console.print(Panel(emergency_msg, style="bold yellow", border_style="bold red", box=box.HEAVY))

    def cmd_heading(self, args):
        if not args:
            env = self.sim.environment
            self.console.print(f"[cyan]Heading: {env.heading:.1f}° ({env.compass_bearing}) | Target: {env.target_heading:.1f}°[/cyan]")
            return
        try:
            deg = float(args[0]) % 360
            self.sim.environment.set_heading(deg)
            self.console.print(f"[cyan]HELM ORDER: New heading {deg:.0f}° ({self.sim.environment.compass_bearing})[/cyan]")
        except ValueError:
            self.console.print("[red]Usage: heading <degrees>[/red]")

    def cmd_throttle(self, args):
        if not args:
            self.console.print(f"[cyan]Throttle: {self.sim.environment.throttle}% | Speed: {self.sim.environment.speed:.1f} kt[/cyan]")
            return
        try:
            pct = int(args[0])
            self.sim.environment.set_throttle(pct)
            self.console.print(f"[cyan]THROTTLE: Set to {self.sim.environment.throttle}%[/cyan]")
        except ValueError:
            self.console.print("[red]Usage: throttle <0-100>[/red]")

    def cmd_ballast(self, args):
        env = self.sim.environment
        if not args or args[0] == "status":
            level = env.ballast_level
            bar = "█" * int(level / 5) + "░" * (20 - int(level / 5))
            self.console.print(f"[cyan]Ballast Level: [{bar}] {level:.0f}%[/cyan]")
            self.console.print(f"[dim]  (0%=buoyant/empty  100%=heavy/flooded)[/dim]")
            return
        action = args[0].lower()
        if action in ("flood", "blow"):
            env.set_ballast(action)
            self.console.print(f"[cyan]BALLAST: {action.upper()} — Level now {env.ballast_level:.0f}%[/cyan]")
        else:
            self.console.print("[red]Usage: ballast <flood|blow|status>[/red]")

    def cmd_nav(self):
        env = self.sim.environment
        
        # Create a structured table for the nav data
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Key", style="dim", width=12)
        table.add_column("Value", style="bold cyan", width=30)

        table.add_row("DEPTH", f"{env.depth:>6.1f}m  [dim]{env.depth_direction}[/dim]")
        table.add_row("TARGET", f"{env.target_depth:>6.1f}m")
        table.add_row("HEADING", f"{env.heading:>6.1f}°  → {env.compass_bearing}")
        table.add_row("SPEED", f"{env.speed:>6.2f}kt [dim](throttle {env.throttle}%)[/dim]")
        table.add_row("POSITION", f"{env.latitude:>7.4f}°N  {env.longitude:>8.4f}°W")
        table.add_row("WATER °C", f"{env.water_temperature:>6.1f}")
        table.add_row("PRESSURE", f"{env.pressure_bar:>6.1f} bar")
        
        # Color code the zone
        zone_color = "green" if env.depth < 50 else "yellow" if env.depth < 200 else "red"
        table.add_row("ZONE", f"[{zone_color}]{env.depth_zone.value}[/{zone_color}]")
        
        table.add_row("VISIBILITY", f"{env.visibility_meters:>4.1f}m")
        table.add_row("BALLAST", f"{env.ballast_level:>5.0f}%")
        table.add_row("DIST", f"{env.distance_traveled:>6.2f} nm")
        
        comms_color = "green" if env.signal_strength > 70 else "yellow" if env.signal_strength > 20 else "red"
        table.add_row("COMMS", f"[{comms_color}]{env.comms_status.value}[/{comms_color}] ({env.signal_strength:.0f}%)")

        self.console.print(Panel(
            table, 
            title="[bold cyan]NAVIGATION COMPUTER[/bold cyan]", 
            border_style="cyan",
            expand=False,
            padding=(1, 1)
        ))

    # ════════════════════════════════════════════════════════════════════
    #  SENSORS & COMMS
    # ════════════════════════════════════════════════════════════════════

    def cmd_sonar(self, args):
        env = self.sim.environment
        if not args:
            self.console.print(f"[cyan]Sonar Mode: {env.sonar_mode.value}[/cyan]")
            if env.sonar_contacts:
                self._display_sonar_contacts()
            else:
                self.console.print("[dim]No contacts.[/dim]")
            return

        mode = args[0].lower()
        if mode == "ping":
            self.console.print("[cyan]SONAR: Active ping transmitted...[/cyan]")
            env.set_sonar("active")
            # Step a few times to get contacts
            self.sim.logger.mute()
            for _ in range(3):
                self.sim.step()
            self.sim.logger.unmute()
            self._display_sonar_contacts()
        elif mode in ("active", "passive", "off"):
            env.set_sonar(mode)
            self.console.print(f"[cyan]SONAR: Mode set to {mode.upper()}[/cyan]")
            if mode == "active":
                self.console.print("[yellow]⚠ Active sonar increases detection risk and power draw[/yellow]")
        else:
            self.console.print("[red]Usage: sonar <active|passive|off|ping>[/red]")

    def _display_sonar_contacts(self):
        env = self.sim.environment
        if not env.sonar_contacts:
            self.console.print("[dim]Sonar: No contacts detected.[/dim]")
            return

        table = Table(title="[bold cyan]Sonar Contact Report[/bold cyan]", box=box.ROUNDED, border_style="cyan")
        table.add_column("BRG", style="yellow", justify="right", width=5)
        table.add_column("RNG", style="white", justify="right", width=8)
        table.add_column("Classification", style="bold")
        table.add_column("Conf", justify="right", width=5)

        for c in env.sonar_contacts:
            conf_color = "green" if c['confidence'] > 70 else "yellow" if c['confidence'] > 40 else "red"
            table.add_row(
                f"{c['bearing']}°",
                f"{c['range']}m",
                c['description'],
                f"[{conf_color}]{c['confidence']}%[/{conf_color}]"
            )
        self.console.print(table)

    def cmd_hydrophone(self):
        self.console.print("[bold cyan]Hydrophone Array — Passive Listening Mode[/bold cyan]")
        self.sim.environment.set_sonar("passive")
        self.sim.logger.mute()
        for _ in range(5):
            self.sim.step()
        self.sim.logger.unmute()

        contacts = self.sim.environment.sonar_contacts
        if contacts:
            self._display_sonar_contacts()
        else:
            self.console.print("[dim]  ... ambient ocean noise only. No contacts.[/dim]")

        # Show ambient sound level
        depth = self.sim.environment.depth
        if depth < 50:
            self.console.print("[dim]  Ambient: Surface waves, shipping noise[/dim]")
        elif depth < 200:
            self.console.print("[dim]  Ambient: Thermocline layer, biologic sounds[/dim]")
        else:
            self.console.print("[dim]  Ambient: Deep ocean — minimal noise floor[/dim]")

    def cmd_sensors(self):
        env = self.sim.environment
        stats = self.sim.resource_manager.stats()

        grid = Table.grid(expand=True, padding=1)
        grid.add_column()
        grid.add_column()

        grid.add_row(
            Panel(
                f"[bold]Depth:[/bold]      {env.depth:.1f}m\n"
                f"[bold]Pressure:[/bold]   {env.pressure_bar:.1f} bar\n"
                f"[bold]Water °C:[/bold]   {env.water_temperature:.1f}°C\n"
                f"[bold]Visibility:[/bold] {env.visibility_meters:.1f}m\n"
                f"[bold]Zone:[/bold]       {env.depth_zone.value}\n"
                f"[bold]Hull:[/bold]       {env.hull_integrity:.1f}%",
                title="Environmental", border_style="cyan"
            ),
            Panel(
                f"[bold]Heading:[/bold]    {env.heading:.1f}° {env.compass_bearing}\n"
                f"[bold]Speed:[/bold]      {env.speed:.2f} kt\n"
                f"[bold]Throttle:[/bold]   {env.throttle}%\n"
                f"[bold]Ballast:[/bold]    {env.ballast_level:.0f}%\n"
                f"[bold]Position:[/bold]   {env.latitude:.4f}°N\n"
                f"               {env.longitude:.4f}°W",
                title="Navigation", border_style="yellow"
            ),
        )
        grid.add_row(
            Panel(
                f"[bold]Battery:[/bold]    {stats['battery_soc']:.0f}% ({stats['charge_state']})\n"
                f"[bold]Voltage:[/bold]    {stats['pack_voltage']:.2f}V\n"
                f"[bold]Cell Temp:[/bold]  {stats['avg_temp']:.1f}°C avg\n"
                f"[bold]Healthy:[/bold]    {stats['healthy_cells']}/{stats['total_cells']} cells\n"
                f"[bold]Throttle:[/bold]   {'YES' if stats['thermal_throttle'] else 'No'}\n"
                f"[bold]ETA:[/bold]        {stats['eta_minutes']:.0f} min",
                title="Power", border_style="green"
            ),
            Panel(
                f"[bold]Comms:[/bold]      {env.comms_status.value}\n"
                f"[bold]Signal:[/bold]     {env.signal_strength:.0f}%\n"
                f"[bold]Sonar:[/bold]      {env.sonar_mode.value}\n"
                f"[bold]Contacts:[/bold]   {len(env.sonar_contacts)}\n"
                f"[bold]Memory:[/bold]     {stats['memory_pressure']}\n"
                f"[bold]Scheduler:[/bold]  {self.sim.metrics.scheduler_name.upper()}",
                title="Systems", border_style="magenta"
            ),
        )
        self.console.print(grid)

    def cmd_comms(self, args):
        env = self.sim.environment
        if not args or args[0] == "status":
            status_color = {
                "ONLINE": "green", "DEGRADED": "yellow",
                "LOS_ONLY": "red", "OFFLINE": "bold red"
            }.get(env.comms_status.value, "white")

            self.console.print(f"[bold cyan]Communications Status[/bold cyan]")
            self.console.print(f"  Status:   [{status_color}]{env.comms_status.value}[/{status_color}]")
            self.console.print(f"  Signal:   {env.signal_strength:.0f}%")
            self.console.print(f"  Depth:    {env.depth:.0f}m (attenuation factor: {max(0, 100 - env.depth):.0f}%)")
            self.console.print(f"  Encrypt:  AES-256")
            return

        if args[0] == "send":
            if env.comms_status.value == "OFFLINE":
                self.console.print("[bold red]COMMS: Cannot transmit — no signal at current depth[/bold red]")
            elif env.comms_status.value == "DEGRADED":
                self.console.print("[yellow]COMMS: Message queued — degraded signal, may be delayed[/yellow]")
            else:
                self.console.print("[green]COMMS: Message transmitted successfully[/green]")

    def cmd_hull(self):
        env = self.sim.environment
        integrity = env.hull_integrity
        color = "green" if integrity > 80 else "yellow" if integrity > 50 else "bold red"
        stress = env.hull_stress_factor

        bar_len = 30
        filled = int(integrity / 100 * bar_len)
        hull_bar = "█" * filled + "░" * (bar_len - filled)

        self.console.print(Panel(
            f"[bold]Hull Integrity:[/bold] [{color}][{hull_bar}] {integrity:.1f}%[/{color}]\n\n"
            f"  Depth:          {env.depth:.1f}m\n"
            f"  Pressure:       {env.pressure_bar:.1f} bar\n"
            f"  Max Rated:      {env.max_rated_depth:.0f}m\n"
            f"  Stress Factor:  {'[green]' if stress < 1.5 else '[yellow]' if stress < 2.5 else '[red]'}{stress:.2f}x{'[/green]' if stress < 1.5 else '[/yellow]' if stress < 2.5 else '[/red]'}\n"
            f"  Depth Margin:   {max(0, env.max_rated_depth - env.depth):.0f}m remaining",
            title="[bold cyan]Hull Integrity Monitor[/bold cyan]",
            border_style="cyan",
        ))

    def cmd_ping(self, args):
        target = args[0] if args else "SURFACE_SHIP"
        env = self.sim.environment

        self.console.print(f"[cyan]PING {target}...[/cyan]")
        if env.comms_status.value == "OFFLINE":
            self.console.print(f"[bold red]  Request timed out — no signal at {env.depth:.0f}m depth[/bold red]")
            return

        # Simulate latency based on depth
        latency = 50 + env.depth * 2 + random.randint(0, 100)
        loss = 0 if env.comms_status.value == "ONLINE" else random.randint(20, 60)

        for i in range(4):
            if random.randint(0, 100) < loss:
                self.console.print(f"  [red]Request timed out.[/red]")
            else:
                ms = latency + random.randint(-20, 40)
                self.console.print(f"  Reply from {target}: time={ms}ms TTL=64")
            time.sleep(0.1)

        self.console.print(f"[dim]--- {target} ping statistics ---[/dim]")
        self.console.print(f"[dim]4 packets transmitted, {4 - int(loss * 4 / 100)} received, {loss}% loss[/dim]")

    # ════════════════════════════════════════════════════════════════════
    #  BATTERY MANAGEMENT
    # ════════════════════════════════════════════════════════════════════

    def cmd_battery(self):
        bms = self.sim.resource_manager.bms
        stats_data = bms.stats()

        # Pack header
        soc = stats_data['pack_soc']
        cs = stats_data['charge_state']
        soc_color = "green" if soc > 50 else "yellow" if soc > 20 else "bold red"

        # Build cell display
        cell_lines = []
        for cell_data in stats_data['cells']:
            cell = bms.cells[cell_data['id']]
            soc_val = cell_data['soc']
            bar_len = 10
            filled = int(soc_val / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)

            health_icon = cell.status_icon()
            health_color = "green" if cell_data['health'] == "OK" else "yellow" if cell_data['health'] == "DEGRADED" else "red"

            temp = cell_data['temp']
            temp_color = "green" if temp < 35 else "yellow" if temp < 50 else "bold red"

            cell_lines.append(
                f"  CELL {cell_data['id']}: [{bar}] {cell_data['voltage']:.3f}V  "
                f"[{temp_color}]{temp:>4.1f}°C[/{temp_color}]  "
                f"[{health_color}]{health_icon} {cell_data['health']:<8s}[/{health_color}]  "
                f"{cell_data['resistance_mohm']:.1f}mΩ"
            )

        cell_block = "\n".join(cell_lines)

        # ETA
        eta = stats_data['eta_minutes']
        eta_str = f"{int(eta // 60)}h {int(eta % 60)}m" if eta < 999 else "∞"

        throttle_str = "[bold red]ACTIVE — Power draw reduced 40%[/bold red]" if stats_data['thermal_throttle'] else "[green]Inactive[/green]"

        content = (
            f"[bold]Pack SOC:[/bold]    [{soc_color}]{soc:.1f}%[/{soc_color}] ({cs})\n"
            f"[bold]Voltage:[/bold]     {stats_data['pack_voltage']:.2f}V (2S4P)\n"
            f"[bold]Cells:[/bold]       {stats_data['healthy_cells']}/{stats_data['total_cells']} healthy\n"
            f"[bold]Avg Temp:[/bold]    {stats_data['avg_temp']:.1f}°C  (Max: {stats_data['max_temp']:.1f}°C)\n"
            f"[bold]Thermal:[/bold]     {throttle_str}\n"
            f"[bold]Mission ETA:[/bold] {eta_str}\n"
            f"\n{'─' * 55}\n{cell_block}\n{'─' * 55}\n"
            f"\n[dim]  Config: 2S4P Li-Ion 18650 | Nominal: 7.4V | {bms.total_capacity_wh:.0f} Wh[/dim]"
        )

        self.console.print(Panel(
            content,
            title="[bold cyan]Battery Management System[/bold cyan]",
            border_style="green",
            box=box.DOUBLE,
        ))

    # ════════════════════════════════════════════════════════════════════
    #  SYSTEM INFO
    # ════════════════════════════════════════════════════════════════════

    def cmd_sysinfo(self):
        stats = self.sim.resource_manager.stats()
        metrics = self.sim.get_results()
        env = self.sim.environment

        grid = Table.grid(expand=True, padding=1)
        grid.add_column()
        grid.add_column()

        grid.add_row(
            Panel(f"[bold cyan]Hardware Telemetry[/bold cyan]\n"
                  f"Uptime: {self.sim.time} ticks\n"
                  f"Peak RAM: {stats['peak_memory_usage']} units\n"
                  f"Alloc Failures: {stats['alloc_failures']}\n"
                  f"Energy Spent: {stats['total_energy_consumed']:.1f} W\n"
                  f"Hull: {env.hull_integrity:.1f}%\n"
                  f"Depth: {env.depth:.0f}m | Pressure: {env.pressure_bar:.1f} bar",
                  title="Hardware Health", border_style="blue"),
            Panel(f"Tasks Completed: {metrics['tasks_completed']}\n"
                  f"Throughput: {metrics['throughput']:.3f} tps\n"
                  f"Context Switches: {metrics['context_switches']}\n"
                  f"Avg Waiting: {metrics['average_waiting_time']:.1f} ticks\n"
                  f"Deadline Miss: {metrics['deadline_miss_rate']*100:.1f}%\n"
                  f"Fault Rate: {metrics['fault_rate']:.4f} /step",
                  title="Scheduler Efficiency", border_style="magenta")
        )

        self.console.print(grid)

    def cmd_uptime(self):
        now = datetime.datetime.now()
        uptime = now - self._boot_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        tasks = self.sim.kernel.scheduler.get_queued_tasks()
        running = sum(1 for t in tasks if t.state == TaskState.RUNNING)
        total = len(tasks)
        load = running / max(total, 1) * 100

        self.console.print(f"[cyan]  {now.strftime('%H:%M:%S')} up {hours}:{minutes:02d}:{seconds:02d}[/cyan]")
        self.console.print(f"[cyan]  Kernel time: {self.sim.time} ticks[/cyan]")
        self.console.print(f"[cyan]  Load average: {load:.1f}% ({running} running, {total} total)[/cyan]")
        self.console.print(f"[cyan]  Mission: {self._mission_id}[/cyan]")

    def cmd_free(self):
        stats = self.sim.resource_manager.stats()
        used = stats['total_memory'] - stats['available_memory']

        table = Table(title="[bold cyan]Memory Usage[/bold cyan]", box=box.SIMPLE_HEAD)
        table.add_column("", style="bold")
        table.add_column("Total", justify="right")
        table.add_column("Used", justify="right")
        table.add_column("Free", justify="right")
        table.add_column("Pressure", justify="center")

        table.add_row(
            "Mem",
            str(stats['total_memory']),
            str(used),
            str(stats['available_memory']),
            f"[{'green' if stats['memory_pressure'] == 'LOW' else 'yellow' if stats['memory_pressure'] == 'MEDIUM' else 'red'}]{stats['memory_pressure']}[/]",
        )
        table.add_row(
            "Peak",
            str(stats['total_memory']),
            str(stats['peak_memory_usage']),
            str(stats['total_memory'] - stats['peak_memory_usage']),
            "",
        )
        self.console.print(table)
        self.console.print(f"[dim]  Fragmentation ratio: {stats['fragmentation_ratio']:.4f}  |  Alloc failures: {stats['alloc_failures']}[/dim]")

    def cmd_df(self):
        stats = self.sim.resource_manager.stats()
        mem_pct = stats['memory_utilization'] * 100

        table = Table(title="[bold cyan]Filesystem Usage[/bold cyan]", box=box.SIMPLE_HEAD)
        table.add_column("Filesystem", style="bold")
        table.add_column("Size", justify="right")
        table.add_column("Used", justify="right")
        table.add_column("Avail", justify="right")
        table.add_column("Use%", justify="right")
        table.add_column("Mounted on")

        used = stats['total_memory'] - stats['available_memory']
        table.add_row("/dev/mem0", str(stats['total_memory']), str(used), str(stats['available_memory']), f"{mem_pct:.0f}%", "/")
        table.add_row("/dev/flash0", "256", "34", "222", "13%", "/var/log")
        table.add_row("/dev/bbx0", "64", f"{min(64, self.sim.time // 5)}", f"{max(0, 64 - self.sim.time // 5)}", f"{min(100, self.sim.time // 5 * 100 // 64):.0f}%", "/blackbox")
        self.console.print(table)

    def cmd_who(self):
        env = self.sim.environment
        self.console.print("[bold cyan]Connected Operators[/bold cyan]")
        self.console.print(f"  {self._operator:<20s} console    {self._boot_time.strftime('%H:%M')}   (local)")
        if env.comms_status.value in ("ONLINE", "DEGRADED"):
            self.console.print(f"  {'SURFACE_OPS':<20s} rf-link    {self._boot_time.strftime('%H:%M')}   ({env.comms_status.value.lower()})")
        else:
            self.console.print(f"  [dim]{'SURFACE_OPS':<20s} rf-link    --:--   (disconnected)[/dim]")

    def cmd_dmesg(self):
        logs = self.sim.logger.get_recent_logs(50)
        self.console.print("[bold cyan]Kernel Message Buffer (dmesg)[/bold cyan]")
        self.console.print("─" * 70)
        for log in logs:
            if "[ERROR]" in log or "FAILED" in log or "Fault" in log:
                self.console.print(f"  [red]{log}[/red]")
            elif "[WARNING]" in log or "PHASE" in log:
                self.console.print(f"  [yellow]{log}[/yellow]")
            elif "COMPLETED" in log:
                self.console.print(f"  [green]{log}[/green]")
            elif "suspended" in log.lower():
                self.console.print(f"  [magenta]{log}[/magenta]")
            elif "AI" in log:
                self.console.print(f"  [cyan]{log}[/cyan]")
            else:
                self.console.print(f"  [dim]{log}[/dim]")

    # ════════════════════════════════════════════════════════════════════
    #  AUDIT & BLACKBOX
    # ════════════════════════════════════════════════════════════════════

    def cmd_audit(self):
        """Live log audit stream."""
        self.console.print("[bold cyan]Entering Ghost Mode Audit Stream. Press Ctrl+C to exit.[/bold cyan]")
        self.sim.logger.mute()
        try:
            with Live(self._generate_log_panel(), refresh_per_second=4, screen=True) as live:
                while True:
                    self.sim.step()
                    live.update(self._generate_log_panel())
                    time.sleep(0.25)
        except KeyboardInterrupt:
            self.sim.logger.unmute()
        finally:
            self.sim.logger.unmute()
            self.console.print("\n[dim]Audit stream closed.[/dim]")

    def _generate_log_panel(self) -> Panel:
        logs = self.sim.logger.get_recent_logs(18)
        log_text = Text()
        for log in logs:
            if "[ERROR]" in log or "Fault" in log or "MISSED" in log or "FAILED" in log:
                log_text.append(log + "\n", style="bold red")
            elif "[WARNING]" in log or "PHASE" in log:
                log_text.append(log + "\n", style="yellow")
            elif "COMPLETED" in log:
                log_text.append(log + "\n", style="green")
            elif "suspended" in log.lower():
                log_text.append(log + "\n", style="magenta")
            elif "AI" in log:
                log_text.append(log + "\n", style="cyan")
            elif "I/O complete" in log:
                log_text.append(log + "\n", style="blue")
            else:
                log_text.append(log + "\n", style="dim")

        env = self.sim.environment
        stats = self.sim.resource_manager.stats()
        subtitle = (
            f"T={self.sim.time} | PWR:{stats['battery_soc']:.0f}% | "
            f"DEPTH:{env.depth:.0f}m | {stats['mission_mode']}"
        )

        return Panel(log_text, title="Kernel Audit Trail", border_style="cyan", subtitle=subtitle)

    def cmd_blackbox(self):
        """Export mission telemetry."""
        filename = f"blackbox_{self._mission_id}_{datetime.datetime.now().strftime('%H%M%S')}.json"
        filepath = os.path.join(os.getcwd(), filename)

        data = {
            "mission_id": self._mission_id,
            "operator": self._operator,
            "timestamp": datetime.datetime.now().isoformat(),
            "kernel_time": self.sim.time,
            "metrics": self.sim.metrics.to_dict(),
            "resource_stats": self.sim.resource_manager.stats(),
            "environment": self.sim.environment.snapshot(),
            "battery_cells": self.sim.resource_manager.bms.stats(),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self.console.print(f"[bold green]✔ Blackbox data exported → {filename}[/bold green]")
        self.console.print(f"[dim]  {len(data['metrics'])} KPIs | {self.sim.time} ticks | {data['resource_stats']['battery_soc']:.0f}% SOC[/dim]")

    # ════════════════════════════════════════════════════════════════════
    #  EMERGENCY
    # ════════════════════════════════════════════════════════════════════

    def cmd_emergency(self):
        emergency_msg = (
            "  ╔══════════════════════════════════════════════╗\n"
            "  ║      🚨  EMERGENCY PROTOCOL ACTIVATED  🚨   ║\n"
            "  ╠══════════════════════════════════════════════╣\n"
            "  ║  1. Ballast tanks: EMERGENCY BLOW            ║\n"
            "  ║  2. Thrusters: MAX SURFACE                   ║\n"
            "  ║  3. Distress beacon: TRANSMITTING           ║\n"
            "  ║  4. Non-critical systems: SUSPENDED         ║\n"
            "  ║  5. Blackbox: RECORDING                     ║\n"
            "  ╚══════════════════════════════════════════════╝"
        )
        self.console.print(Panel(emergency_msg, style="bold red", border_style="bold red", box=box.HEAVY))

        # Execute emergency actions
        self.sim.environment.set_surface()
        self.sim.environment.set_throttle(100)
        if self.sim.resource_manager.mission_mode != "Survival":
            self.sim.resource_manager.trigger_survival()
        self.cmd_blackbox()
        self.console.print("[bold yellow]All hands — prepare for emergency surface.[/bold yellow]")

    # ════════════════════════════════════════════════════════════════════
    #  MISSION MODE
    # ════════════════════════════════════════════════════════════════════

    def cmd_mission(self, args):
        if not args:
            mode = self.sim.resource_manager.mission_mode
            phase = self.sim.resource_manager.survival_phase
            phase_str = f" (Phase {phase})" if phase > 0 else ""
            self.console.print(f"Current Mission State: [bold cyan]{mode}{phase_str}[/bold cyan]")
            return

        mode = args[0].lower()
        if mode in ("connect", "connected", "human"):
            self.sim.resource_manager.trigger_connected()
            self.sim._last_survival_phase = 0
            self.console.print("[bold green]UPLINK ESTABLISHED. All systems restored to nominal.[/bold green]")
            self.console.print("[dim]  Battery recharged. Memory restored. Fault rates normalized.[/dim]")
        elif mode in ("survive", "survival", "autonomous"):
            self.sim.resource_manager.trigger_survival()
            survival_msg = (
                "  ╔══════════════════════════════════════════════╗\n"
                "  ║   ⚠ UPLINK LOST — AUTONOMOUS MODE          ║\n"
                "  ║   Battery: Emergency reserves only          ║\n"
                "  ║   Memory: Degraded — hardware failures      ║\n"
                "  ║   Fault rates: ELEVATED                      ║\n"
                "  ║   Survival phases will activate as power     ║\n"
                "  ║   depletes. Monitor with 'battery' command.  ║\n"
                "  ╚══════════════════════════════════════════════╝"
            )
            self.console.print(Panel(survival_msg, style="bold red", border_style="bold red", box=box.HEAVY))
        else:
            self.console.print(f"[red]Error:[/red] Unknown mission mode '{mode}'. Use 'connect' or 'survive'.")

    def cmd_sched(self, args):
        if not args:
            self.console.print(f"Current Policy: [bold yellow]{self.sim.metrics.scheduler_name.upper()}[/bold yellow]")
            return
        policy = args[0].lower()
        if policy in ("hybrid", "edf", "priority", "rr"):
            self.sim.set_scheduler(policy)
            self.console.print(f"[bold green]Kernel re-scheduled via {policy.upper()}[/bold green]")
        else:
            self.console.print(f"[red]Error:[/red] Unknown policy '{policy}'. Options: hybrid, edf, priority, rr")

    # ════════════════════════════════════════════════════════════════════
    #  TOP (HTOP-style dashboard)
    # ════════════════════════════════════════════════════════════════════

    def cmd_top(self):
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
        env = self.sim.environment
        tasks = self.sim.kernel.scheduler.get_queued_tasks()

        # 1. Resource Gauges
        mem_used = stats['total_memory'] - stats['available_memory']
        mem_pct = stats['memory_utilization'] * 100
        mem_bar = Progress(BarColumn(bar_width=None), TextColumn("{task.percentage:>3.0f}%"))
        mem_bar.add_task("", total=100, completed=mem_pct)

        batt_pct = stats['battery_soc']
        batt_bar = Progress(BarColumn(bar_width=None), TextColumn("{task.percentage:>3.0f}%"))
        batt_bar.add_task("", total=100, completed=batt_pct)

        header_table = Table.grid(expand=True)
        header_table.add_column(ratio=1)
        header_table.add_column(ratio=1)
        header_table.add_column(ratio=1)
        header_table.add_row(
            Panel(Group(f"Memory: {mem_used}/{stats['total_memory']} units", mem_bar),
                  title="RAM", border_style="blue"),
            Panel(Group(f"Battery: {stats['battery_soc']:.0f}% ({stats['charge_state']})", batt_bar),
                  title="Power", border_style="green"),
            Panel(f"Depth: {env.depth:.0f}m ({env.depth_zone.value})\n"
                  f"Heading: {env.heading:.0f}° {env.compass_bearing}\n"
                  f"Speed: {env.speed:.1f}kt",
                  title="Vehicle", border_style="cyan"),
        )

        # 2. Process Table with all 7 states
        proc_table = Table(expand=True, box=box.SIMPLE_HEAD)
        proc_table.add_column("TID", style="dim", width=4)
        proc_table.add_column("TYPE", width=4)  # SRV vs JOB
        proc_table.add_column("SUBSYSTEM", style="bold cyan", width=18)
        proc_table.add_column("PRI", justify="right", width=4)
        proc_table.add_column("EFF", style="bold magenta", justify="right", width=5)
        proc_table.add_column("STATE", justify="center", width=20)
        proc_table.add_column("CPU", justify="right", width=4)
        proc_table.add_column("MEM", justify="right", width=4)
        proc_table.add_column("DEADLINE", style="yellow", justify="right", width=8)
        proc_table.add_column("PROGRESS", width=12)

        for t in tasks[:18]:
            state_label = t.state_label()
            state_color = self._state_color(t.state.value)

            prio_eff = str(t.effective_priority)
            if t.ai_boost > 0:
                prio_eff = f"[bold magenta]{prio_eff}⚡[/bold magenta]"

            prog_val = ((t.burst_time - max(0, t.remaining_time)) / max(1, t.burst_time)) * 100
            prog_bar = Progress(BarColumn(bar_width=10), console=self.console)
            prog_bar.add_task("", total=100, completed=min(100, prog_val))

            type_label = "[bold blue]SRV[/bold blue]" if t.is_service else "[dim]JOB[/dim]"
            crit_marker = "★" if t.critical else ""

            proc_table.add_row(
                str(t.tid),
                type_label,
                f"{crit_marker}{t.task_type}",
                str(t.base_priority),
                prio_eff,
                f"[{state_color}]{state_label}[/{state_color}]",
                str(t.cpu_ticks),
                str(t.memory_required),
                str(t.deadline) if t.deadline else "-",
                prog_bar,
            )

        # 3. State summary
        state_counts = {}
        for t in tasks:
            s = t.state.value
            state_counts[s] = state_counts.get(s, 0) + 1

        state_items = []
        for state_name in ["NEW", "READY", "RUNNING", "BLOCKED", "WAITING", "SUSPENDED", "FAULT", "TERMINATED"]:
            count = state_counts.get(state_name, 0)
            if count > 0 or state_name in ("READY", "RUNNING"):
                color = self._state_color(state_name)
                state_items.append(f"[{color}]{state_name}:{count}[/{color}]")

        metrics = self.sim.metrics.to_dict()
        mode_color = "green" if stats['mission_mode'] == "Connected" else "bold red"
        phase_str = f" P{stats['survival_phase']}" if stats['survival_phase'] > 0 else ""

        kpi_text = (
            f"T={self.sim.time} │ [{mode_color}]{stats['mission_mode'].upper()}{phase_str}[/{mode_color}] │ "
            f"SCHED:[bold yellow]{self.sim.metrics.scheduler_name.upper()}[/bold yellow] │ "
            f"Compl:[green]{metrics['task_completion_rate']*100:.0f}%[/green] │ "
            f"Miss:[red]{metrics['deadline_miss_rate']*100:.0f}%[/red] │ "
            f" │ ".join(state_items)
        )

        layout = Layout()
        layout.split(
            Layout(header_table, name="header", size=5),
            Layout(Panel(proc_table, title="Kernel Process Monitor", border_style="white"), name="body"),
            Layout(Panel(kpi_text, box=box.MINIMAL), name="footer", size=3)
        )
        return layout

    # ════════════════════════════════════════════════════════════════════
    #  PS (Process List)
    # ════════════════════════════════════════════════════════════════════

    def cmd_ps(self):
        """Live-updating process list."""
        self.console.print("[bold cyan]Opening Process Monitor (Ghost Mode).[/bold cyan]")
        self.sim.logger.mute()
        try:
            with Live(self._generate_ps_table(), refresh_per_second=4, screen=True) as live:
                while True:
                    self.sim.step()
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
        proc_table.add_column("TYPE", width=4)
        proc_table.add_column("SUBSYSTEM", style="bold cyan", width=18)
        proc_table.add_column("PRI", justify="right", width=4)
        proc_table.add_column("AI-BOOST", style="bold magenta", justify="right", width=9)
        proc_table.add_column("STATE", justify="center", width=20)
        proc_table.add_column("MEM", justify="right", width=4)
        proc_table.add_column("FAULTS", justify="right", width=6)
        proc_table.add_column("PROGRESS", width=12)

        for t in tasks[:20]:
            # UI Fix: If this was the task that just ran, show it as RUNNING
            # otherwise it resets to READY before the UI can draw it.
            is_active = (t == self.sim.prev_task and t.state != TaskState.TERMINATED)
            display_state = "RUNNING" if is_active else t.state.value
            
            state_label = t.state_label() if not is_active else "RUNNING"
            state_color = self._state_color(display_state)

            prog_val = ((t.burst_time - max(0, t.remaining_time)) / max(1, t.burst_time)) * 100
            prog_bar = Progress(BarColumn(bar_width=10))
            prog_bar.add_task("", total=100, completed=min(100, prog_val))

            type_label = "[bold blue]SRV[/bold blue]" if t.is_service else "[dim]JOB[/dim]"
            crit = "★" if t.critical else ""

            boost_label = f"+{t.ai_boost}" if t.ai_boost > 0 else "0"
            if t.ai_boost >= 8:
                boost_label = f"[bold magenta]{boost_label} ★[/bold magenta]"

            proc_table.add_row(
                str(t.tid), type_label, f"{crit}{t.task_type}", str(t.base_priority), boost_label,
                f"[{state_color}]{state_label}[/{state_color}]",
                str(t.memory_required), str(t.total_faults), prog_bar,
            )

        # State summary
        state_counts = {}
        for t in tasks:
            s = t.state.value
            state_counts[s] = state_counts.get(s, 0) + 1

        summary_parts = []
        for s in ["READY", "RUNNING", "BLOCKED", "WAITING", "SUSPENDED", "FAULT"]:
            c = state_counts.get(s, 0)
            if c > 0:
                summary_parts.append(f"[{self._state_color(s)}]{s}:{c}[/{self._state_color(s)}]")

        subtitle = f"Total: {len(tasks)} │ " + " │ ".join(summary_parts) if summary_parts else f"Total: {len(tasks)}"

        return Panel(proc_table, title="Active Kernel Threads", border_style="white", subtitle=subtitle)

    # ════════════════════════════════════════════════════════════════════
    #  AI ADVISORY WRAPPERS
    # ════════════════════════════════════════════════════════════════════

    def cmd_advisory_wrap(self):
        cmd_advisory(self.sim, self.console)

    def cmd_predict_wrap(self):
        cmd_predict(self.sim, self.console)

    def cmd_prioritize_wrap(self):
        cmd_prioritize(self.sim, self.console)

    def cmd_compare_wrap(self):
        cmd_compare(self.sim, self.console)

    def cmd_fault(self, args):
        if not args or args[0] != "inject":
            self.console.print("[red]Usage: fault inject <service_name>[/red]")
            self.console.print("[dim]Services: BatteryMonitor, Navigation, O2Scrubber, HullIntegrity[/dim]")
            return
        
        if len(args) < 2:
            self.console.print("[red]Usage: fault inject <service_name>[/red]")
            return
            
        service = args[1]
        result = self.sim.fault_injector.inject(service_name=service)
        
        self.console.print(f"\n  [bold red][FAULT INJECTED] → {service}[/bold red]")
        self.console.print(f"  Fault type: [yellow]{result.fault_type}[/yellow]")
        self.console.print(f"  Severity:   [bold]{result.severity}[/bold]")
        self.console.print()
        self.console.print(f"  [bold cyan]AI RESPONSE:[/bold cyan]")
        
        prob = self.sim.ai_advisor.predict_for_service(service)
        boost = self.sim.ai_advisor.calculate_boost(prob)
        self.console.print(f"  Fault risk spike detected: [red]{prob:.1%}[/red] → Priority boost applied: [bold magenta]+{boost}[/bold magenta]")
        self.console.print(f"  Scheduler updated. Run 'ps' to see priority change.\n")

    def _state_color(self, state: str) -> str:
        return {
            "NEW":        "white",
            "READY":      "blue",
            "RUNNING":    "bold green",
            "BLOCKED":    "red",
            "WAITING":    "yellow",
            "SUSPENDED":  "magenta",
            "FAULT":      "bold red",
            "TERMINATED": "dim",
        }.get(state, "white")
