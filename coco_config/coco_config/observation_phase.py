"""Sensor-only deterministic phase evidence; phase times come from control events.

A baseline is historical context, never a replacement for a live measurement.
This instrument has no simulator/evaluator input and grants no motion authority.
"""
from .object_observation import validated_height

PHASES = ("baseline", "approach", "lift", "release")

class PhaseValidator:
    def __init__(self, colour):
        self.colour = colour
        self.phase = None
        self.started_ns = 0
        self.last_stamp = 0
        self.identity = None

    def transition(self, phase, stamp_ns):
        if phase not in PHASES or not isinstance(stamp_ns, int) or stamp_ns <= 0:
            raise ValueError("Invalid phase event")
        if stamp_ns < self.started_ns:
            raise ValueError("Phase clock moved backwards")
        self.phase, self.started_ns = phase, stamp_ns
        # No cached valid observation survives a phase boundary.
        self.last_stamp = 0

    def record(self, observation, now_ns):
        o = observation if isinstance(observation, dict) else {}
        value = validated_height(o, now_ns=now_ns, colour=self.colour)
        stamp = o.get("stamp_ns", 0)
        reason = o.get("reason", "MALFORMED")
        if value is not None:
            if self.phase is None:
                reason = "PHASE_UNAVAILABLE"
            elif stamp <= self.started_ns:
                reason = "PRE_TRANSITION_SAMPLE"
            elif stamp <= self.last_stamp:
                reason = "NON_MONOTONIC_SAMPLE"
            elif self.identity is not None and (o["track_id"], o["reference_id"]) != self.identity:
                reason = "ASSOCIATION_OR_REFERENCE_CHANGED"
            else:
                reason = "VALID"
                self.identity = (o["track_id"], o["reference_id"])
                self.last_stamp = stamp
        elif reason == "VALID":
            reason = "CONSUMER_REJECTED"
        return dict(phase=self.phase, phase_started_ns=self.started_ns,
                    checked_at_ns=now_ns, contract_valid=reason == "VALID",
                    rejection_reason=reason, observation=o,
                    source_age_s=(now_ns-stamp)/1e9 if isinstance(stamp,int) and stamp else None)

    def reacquire(self, colour):
        self.colour = colour
        self.identity = None
        self.phase = None
        self.started_ns = self.last_stamp = 0
