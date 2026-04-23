"""
sentinel_os/components/environment.py
---------------------------------------
Simulated underwater environment for the SentinelOS AUV.

Tracks the physical state of the vehicle and water:
  - Depth (0-500m), heading, speed
  - Water temperature (decreases with depth)
  - Hydrostatic pressure
  - Visibility / sonar effectiveness
  - Simulated sonar contacts
  - Position tracking (lat/lon estimate)
"""

import random
import math
from enum import Enum


class DepthZone(str, Enum):
    SURFACE    = "SURFACE"      # 0-10m
    SHALLOW    = "SHALLOW"      # 10-50m
    MIDWATER   = "MIDWATER"     # 50-200m
    DEEP       = "DEEP"         # 200-400m
    ABYSS      = "ABYSS"       # 400m+


class SonarMode(str, Enum):
    OFF     = "OFF"
    PASSIVE = "PASSIVE"
    ACTIVE  = "ACTIVE"


class CommsStatus(str, Enum):
    ONLINE     = "ONLINE"       # Full duplex
    DEGRADED   = "DEGRADED"     # Partial signal
    LOS_ONLY   = "LOS_ONLY"    # Line-of-sight only
    OFFLINE    = "OFFLINE"      # No comms


SONAR_CONTACTS = [
    "Whale (biologic)", "Submarine (contact)", "Shipwreck (terrain)",
    "Reef formation", "Thermocline layer", "Undersea cable",
    "Fish school", "Unidentified object", "Rock outcrop",
    "Current anomaly", "Debris field", "Volcanic vent",
    "Anchor chain", "Pipeline", "Mine-like object",
]


class UnderwaterEnvironment:
    """
    Simulates the AUV's physical environment and vehicle state.
    Updated each simulation tick by the SystemSimulator.
    """

    def __init__(self):
        # Vehicle state
        self.depth: float = 0.0             # meters below surface
        self.target_depth: float = 0.0      # dive/surface target
        self.heading: float = 0.0           # degrees (0-360)
        self.target_heading: float = 0.0
        self.speed: float = 0.0             # knots
        self.throttle: int = 0              # 0-100%

        # Position (simulated)
        self.latitude: float = 23.4 + random.uniform(-0.5, 0.5)
        self.longitude: float = -67.8 + random.uniform(-0.5, 0.5)

        # Ballast
        self.ballast_level: float = 50.0    # 0=empty (buoyant), 100=full (sinking)

        # Sonar
        self.sonar_mode: SonarMode = SonarMode.PASSIVE
        self.sonar_contacts: list = []
        self._sonar_sweep_timer: int = 0

        # Comms
        self.comms_status: CommsStatus = CommsStatus.ONLINE
        self.signal_strength: float = 100.0

        # Hull
        self.hull_integrity: float = 100.0  # percentage
        self.max_rated_depth: float = 500.0

        # Accumulated distance
        self.distance_traveled: float = 0.0  # nautical miles

    # ────────────────────────────────────────────────────────────────────
    #  Derived properties
    # ────────────────────────────────────────────────────────────────────

    @property
    def pressure_bar(self) -> float:
        """Hydrostatic pressure in bar (1 bar per ~10m + 1 atm)."""
        return 1.0 + self.depth / 10.0

    @property
    def water_temperature(self) -> float:
        """Water temp decreases with depth (thermocline model)."""
        surface_temp = 24.0
        if self.depth < 20:
            return surface_temp - self.depth * 0.1
        elif self.depth < 100:
            # Thermocline: rapid drop
            return surface_temp - 2.0 - (self.depth - 20) * 0.15
        elif self.depth < 300:
            return surface_temp - 14.0 - (self.depth - 100) * 0.03
        else:
            return max(1.5, 4.0 - (self.depth - 300) * 0.005)

    @property
    def visibility_meters(self) -> float:
        """Underwater visibility decreases with depth."""
        base = 30.0
        if self.depth < 50:
            return base - self.depth * 0.2
        elif self.depth < 200:
            return max(2, 20 - (self.depth - 50) * 0.1)
        return max(0.5, 5 - (self.depth - 200) * 0.015)

    @property
    def depth_zone(self) -> DepthZone:
        if self.depth < 10:
            return DepthZone.SURFACE
        elif self.depth < 50:
            return DepthZone.SHALLOW
        elif self.depth < 200:
            return DepthZone.MIDWATER
        elif self.depth < 400:
            return DepthZone.DEEP
        return DepthZone.ABYSS

    @property
    def compass_bearing(self) -> str:
        """Convert heading to compass bearing."""
        bearings = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = int((self.heading + 11.25) / 22.5) % 16
        return bearings[idx]

    @property
    def depth_direction(self) -> str:
        diff = self.target_depth - self.depth
        if abs(diff) < 0.5:
            return "level"
        return "▼ diving" if diff > 0 else "▲ ascending"

    @property
    def hull_stress_factor(self) -> float:
        """Hull stress increases with depth (exponential near max rating)."""
        if self.depth < self.max_rated_depth * 0.5:
            return 1.0
        ratio = self.depth / self.max_rated_depth
        return 1.0 + (ratio ** 3) * 2.0

    # ────────────────────────────────────────────────────────────────────
    #  Tick update
    # ────────────────────────────────────────────────────────────────────

    def tick(self):
        """Advance one simulation step."""
        # Depth movement (Physics-based with ballast/buoyancy)
        depth_diff = self.target_depth - self.depth
        
        # Buoyancy effect: 50% is neutral. 
        # >50 is heavy (downward force), <50 is light (upward force)
        buoyancy = (self.ballast_level - 50.0) * 0.01 
        
        if abs(depth_diff) > 0.1:
            # Base rate from thrusters/throttle
            base_rate = 2.0 + self.throttle * 0.05
            
            # Apply buoyancy: if diving, heavy ballast helps. If ascending, light ballast helps.
            if depth_diff > 0:  # Diving
                rate = min(abs(depth_diff), base_rate + max(0, buoyancy))
                self.depth += rate
            else:  # Ascending
                rate = min(abs(depth_diff), base_rate - min(0, buoyancy))
                self.depth -= rate
                
            self.depth = max(0, min(self.max_rated_depth + 50, self.depth))
        elif abs(buoyancy) > 0.05:
            # Drift due to ballast if not at target or no active thrusting
            # This makes the 100m vs 120m reality: if you are too heavy, you will drift down
            self.depth += buoyancy * 0.2
            self.depth = max(0, min(self.max_rated_depth + 50, self.depth))

        # Heading adjustment (shortest path)
        hdg_diff = (self.target_heading - self.heading + 180) % 360 - 180
        if abs(hdg_diff) > 0.5:
            turn_rate = min(abs(hdg_diff), 3.0)
            self.heading += turn_rate if hdg_diff > 0 else -turn_rate
            self.heading %= 360

        # Speed from throttle (affected by depth/current)
        depth_drag = 1.0 + self.depth / 1000  # deeper = more drag
        self.speed = (self.throttle / 100.0) * 8.0 / depth_drag  # max 8 knots

        # Distance
        self.distance_traveled += self.speed * (1 / 3600)  # per tick ≈ 1 second

        # Position update (simplified)
        if self.speed > 0:
            rad = math.radians(self.heading)
            self.latitude += math.cos(rad) * self.speed * 0.0001
            self.longitude += math.sin(rad) * self.speed * 0.0001

        # Hull integrity (degrades under extreme depth)
        if self.depth > self.max_rated_depth * 0.8:
            stress = ((self.depth / self.max_rated_depth) - 0.8) * 0.1
            self.hull_integrity = max(0, self.hull_integrity - stress)

        # Comms degradation with depth
        if self.depth < 20:
            self.comms_status = CommsStatus.ONLINE
            self.signal_strength = 100 - self.depth * 2
        elif self.depth < 80:
            self.comms_status = CommsStatus.DEGRADED
            self.signal_strength = max(20, 60 - (self.depth - 20))
        elif self.depth < 200:
            self.comms_status = CommsStatus.LOS_ONLY
            self.signal_strength = max(5, 20 - (self.depth - 80) * 0.1)
        else:
            self.comms_status = CommsStatus.OFFLINE
            self.signal_strength = 0

        # Ballast now affects buoyancy in the main tick loop, not the target depth.

        # Sonar contacts update
        self._sonar_sweep_timer += 1
        if self.sonar_mode != SonarMode.OFF and self._sonar_sweep_timer >= 5:
            self._sonar_sweep_timer = 0
            self._update_sonar()

    def _update_sonar(self):
        """Generate sonar contacts based on mode and depth."""
        self.sonar_contacts = []
        num_contacts = random.randint(0, 3)

        # Active sonar detects more
        if self.sonar_mode == SonarMode.ACTIVE:
            num_contacts += random.randint(1, 3)

        for _ in range(num_contacts):
            bearing = random.randint(0, 359)
            range_m = random.randint(50, 2000)
            desc = random.choice(SONAR_CONTACTS)
            confidence = random.randint(40, 99)
            if self.sonar_mode == SonarMode.PASSIVE:
                confidence = max(20, confidence - 30)
            self.sonar_contacts.append({
                "bearing": bearing,
                "range": range_m,
                "description": desc,
                "confidence": confidence,
            })

    # ────────────────────────────────────────────────────────────────────
    #  Commands
    # ────────────────────────────────────────────────────────────────────

    def set_dive(self, target_m: float):
        self.target_depth = max(0, min(self.max_rated_depth + 20, target_m))
        if self.ballast_level < 55:
            self.ballast_level = 65  # auto-flood for dive

    def set_surface(self):
        self.target_depth = 0
        self.ballast_level = 0  # full blow

    def set_heading(self, degrees: float):
        self.target_heading = degrees % 360

    def set_throttle(self, pct: int):
        self.throttle = max(0, min(100, pct))

    def set_ballast(self, action: str):
        if action == "flood":
            self.ballast_level = min(100, self.ballast_level + 20)
        elif action == "blow":
            self.ballast_level = max(0, self.ballast_level - 30)

    def set_sonar(self, mode: str):
        mode_map = {
            "off": SonarMode.OFF,
            "passive": SonarMode.PASSIVE,
            "active": SonarMode.ACTIVE,
        }
        self.sonar_mode = mode_map.get(mode.lower(), SonarMode.PASSIVE)

    def snapshot(self) -> dict:
        """Return the environment state for the system state dict."""
        return {
            "depth": round(self.depth, 1),
            "target_depth": round(self.target_depth, 1),
            "heading": round(self.heading, 1),
            "speed": round(self.speed, 2),
            "throttle": self.throttle,
            "pressure_bar": round(self.pressure_bar, 1),
            "water_temperature": round(self.water_temperature, 1),
            "visibility": round(self.visibility_meters, 1),
            "depth_zone": self.depth_zone.value,
            "hull_integrity": round(self.hull_integrity, 1),
            "comms_status": self.comms_status.value,
            "signal_strength": round(self.signal_strength, 1),
            "ballast_level": round(self.ballast_level, 1),
            "sonar_mode": self.sonar_mode.value,
            "latitude": round(self.latitude, 4),
            "longitude": round(self.longitude, 4),
            "distance_nm": round(self.distance_traveled, 2),
        }
