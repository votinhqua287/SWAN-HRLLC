"""Baseline controllers and fixed SWAN modes (research guide, Section 13).

All baselines are instances of src.controller.Controller with another
weighting, or of the ActionTable with a restricted action set:
  conventional PASS      : arch="pass"   (single waveguide, one RF chain, SA/TDMA)
  SWAN fixed SS          : mode="ss"     (segment selection only)
  SWAN fixed SA / full   : mode="sa"     (always all segments aggregated, TDMA)
  always-full-segment    : mode="full"   (all segments active: full SA or SM)
  rate-maximizing        : scheduler="ratemax"  (expected delivered packets)
  average-delay oriented : scheduler="mw"       (queue-length weights)
  queue-aware non-tail   : scheduler="mw" with energy weight V>0
  M-LWDF / EDF / PF      : scheduler="mlwdf" | "edf" | "pf"
  reactive repositioning : reactive=True (per-slot PA moves with delay tau_r)
"""
from .controller import Controller, user_weight_values  # noqa: F401
from .service import ActionTable  # noqa: F401

BASELINE_CONFIGS = {
    "conventional PASS": dict(arch="pass", scheduler="tas"),
    "SWAN fixed SS": dict(mode="ss", scheduler="tas"),
    "SWAN fixed SA": dict(mode="sa", scheduler="tas"),
    "always-full-segment": dict(mode="full", scheduler="tas"),
    "rate-maximizing": dict(scheduler="ratemax"),
    "average-delay-minimizing": dict(scheduler="mw"),
    "queue-aware non-tail": dict(scheduler="mw", V=0.3, Pc_W=0.1),
    "tail-aware (proposed)": dict(scheduler="tas"),
}
