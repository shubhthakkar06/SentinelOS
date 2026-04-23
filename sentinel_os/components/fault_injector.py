"""
sentinel_os/components/fault_injector.py
------------------------------------------
Advanced Fault Injector for SentinelOS AUV.

Features:
  - Scenario-aware probabilities (Connected vs Survival)
  - Depth-pressure faults (hull stress, seal failures)
  - Temperature cascade faults (overheating equipment)
  - Communications degradation with depth
  - Realistic AUV failure modes
  - Fault deduplication (reports unique events only once per task)
"""

import random


# AUV-specific fault types with descriptions
FAULT_TYPES = {
    "RESOURCE_FAILURE":     "Memory allocation failure",
    "SENSOR_DRIFT":         "Sensor reading out of calibration",
    "COMM_LAG":             "Communications latency spike",
    "IO_TIMEOUT":           "I/O device response timeout",
    "BIT_FLIP":             "Radiation-induced bit flip (SEU)",
    "HULL_STRESS":          "Hull structural stress warning",
    "SEAL_LEAK":            "Pressure seal micro-leak detected",
    "THRUSTER_CAVITATION":  "Thruster blade cavitation",
    "SONAR_INTERFERENCE":   "Acoustic interference on sonar",
    "THERMAL_RUNAWAY":      "Battery cell thermal anomaly",
    "WATER_INGRESS":        "Water detected in compartment",
    "NAVIGATION_DRIFT":     "INS accumulated drift error",
    "POWER_SURGE":          "Voltage spike on power bus",
    "CRYPTO_FAULT":         "Encryption module CRC error",
    "BALLAST_VALVE_STUCK":  "Ballast valve actuator jammed",
}

class FaultResult:
    def __init__(self, fault_type, severity):
        self.fault_type = fault_type
        self.severity = severity


class FaultInjector:
    """
    Injects realistic faults into AUV processes based on
    system state, depth, temperature, and mission mode.
    """

    def __init__(self):
        self._total_faults_injected = 0

    def inject_task_fault(self, task, current_time, system_state=None):
        """
        Evaluate fault conditions and inject appropriate faults.
        Returns a list of fault event dicts.
        """
        faults = []
        mode = system_state.get("mission_mode", "Connected") if system_state else "Connected"
        depth = system_state.get("depth", 0) if system_state else 0
        batt_temp = system_state.get("battery_temp", 25) if system_state else 25
        survival_phase = system_state.get("survival_phase", 0) if system_state else 0

        # ──────────────────────────────────────────────────────────
        # 1. DEADLINE MISS (deterministic — always reported)
        # ──────────────────────────────────────────────────────────
        if task.deadline and current_time > task.deadline:
            if "DEADLINE_MISS" not in task.fault_history:
                task.fault_history.add("DEADLINE_MISS")
                faults.append(self._create_fault(task, current_time, "DEADLINE_MISS"))

        # ──────────────────────────────────────────────────────────
        # 2. BASE TRANSIENT FAULTS (mode-dependent)
        # ──────────────────────────────────────────────────────────
        base_prob = {
            "Connected": 0.02,
            "Survival": 0.08 + survival_phase * 0.03,  # escalates with phase
        }.get(mode, 0.02)

        if random.random() < base_prob:
            # Choose fault type based on task and conditions
            candidates = self._get_fault_candidates(task, depth, batt_temp)
            ftype = random.choice(candidates)

            if ftype not in task.fault_history:
                task.fault_history.add(ftype)
                faults.append(self._create_fault(task, current_time, ftype))

        # ──────────────────────────────────────────────────────────
        # 3. DEPTH-PRESSURE FAULTS
        # ──────────────────────────────────────────────────────────
        if depth > 200:
            pressure_risk = (depth - 200) / 1000  # 0.1 at 300m, 0.3 at 500m
            if survival_phase > 0:
                pressure_risk *= 2

            if random.random() < pressure_risk:
                depth_faults = ["HULL_STRESS", "SEAL_LEAK", "BALLAST_VALVE_STUCK"]
                ftype = random.choice(depth_faults)
                if ftype not in task.fault_history:
                    task.fault_history.add(ftype)
                    faults.append(self._create_fault(task, current_time, ftype))

        # ──────────────────────────────────────────────────────────
        # 4. THERMAL CASCADE FAULTS
        # ──────────────────────────────────────────────────────────
        if batt_temp > 45:
            thermal_risk = (batt_temp - 45) / 50  # escalates linearly
            if random.random() < thermal_risk:
                ftype = "THERMAL_RUNAWAY"
                if ftype not in task.fault_history:
                    task.fault_history.add(ftype)
                    faults.append(self._create_fault(task, current_time, ftype))

        # ──────────────────────────────────────────────────────────
        # 5. COMMS DEGRADATION (depth-dependent)
        # ──────────────────────────────────────────────────────────
        if task.task_type in ("EncryptedComms", "GPSSync") and depth > 100:
            comms_risk = min(0.4, depth / 500)
            if random.random() < comms_risk:
                ftype = "COMM_LAG" if task.task_type == "EncryptedComms" else "NAVIGATION_DRIFT"
                if ftype not in task.fault_history:
                    task.fault_history.add(ftype)
                    faults.append(self._create_fault(task, current_time, ftype))

        # ──────────────────────────────────────────────────────────
        # 6. SURVIVAL MODE ESCALATION
        # ──────────────────────────────────────────────────────────
        if survival_phase >= 3 and random.random() < 0.12:
            emergency_faults = ["WATER_INGRESS", "POWER_SURGE", "RESOURCE_FAILURE"]
            ftype = random.choice(emergency_faults)
            if ftype not in task.fault_history:
                task.fault_history.add(ftype)
                faults.append(self._create_fault(task, current_time, ftype))

        self._total_faults_injected += len(faults)
        return faults

    def _get_fault_candidates(self, task, depth, temp) -> list:
        """Select fault types relevant to the task and conditions."""
        # General faults
        candidates = ["RESOURCE_FAILURE", "IO_TIMEOUT", "BIT_FLIP"]

        # Task-specific faults
        type_faults = {
            "SonarPing": ["SONAR_INTERFERENCE"],
            "Hydrophone": ["SONAR_INTERFERENCE"],
            "ThrusterControl": ["THRUSTER_CAVITATION", "POWER_SURGE"],
            "DepthControl": ["BALLAST_VALVE_STUCK"],
            "BallastPump": ["BALLAST_VALVE_STUCK"],
            "Navigation": ["NAVIGATION_DRIFT", "SENSOR_DRIFT"],
            "EncryptedComms": ["COMM_LAG", "CRYPTO_FAULT"],
            "GPSSync": ["COMM_LAG", "NAVIGATION_DRIFT"],
            "HullIntegrity": ["HULL_STRESS", "SEAL_LEAK"],
            "ThermalRegulation": ["THERMAL_RUNAWAY"],
            "BatteryMonitor": ["POWER_SURGE"],
            "DataLogging": ["IO_TIMEOUT"],
        }
        candidates.extend(type_faults.get(task.task_type, ["SENSOR_DRIFT"]))

        # Depth-specific
        if depth > 300:
            candidates.extend(["HULL_STRESS", "SEAL_LEAK"])

        # Temperature-specific
        if temp > 40:
            candidates.append("THERMAL_RUNAWAY")

        return candidates

    def _create_fault(self, task, time, fault_type):
        return {
            "time": time,
            "task_id": task.tid,
            "fault_type": fault_type,
            "description": FAULT_TYPES.get(fault_type, "Unknown fault"),
        }

    def stats(self) -> dict:
        return {
            "total_faults_injected": self._total_faults_injected,
        }

    def inject(self, service_name=None):
        """Manually inject a fault for demonstration purposes."""
        fault_type = "SENSOR_DRIFT"
        if service_name:
            type_faults = {
                "Navigation": "NAVIGATION_DRIFT",
                "BatteryMonitor": "POWER_SURGE",
                "O2Scrubber": "IO_TIMEOUT",
                "HullIntegrity": "HULL_STRESS"
            }
            fault_type = type_faults.get(service_name, "SENSOR_DRIFT")
        
        severity = random.choice(["LOW", "MEDIUM", "HIGH"])
        self._total_faults_injected += 1
        return FaultResult(fault_type, severity)
