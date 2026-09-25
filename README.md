# Tail-Latency-Aware SWAN for HRLLC under Bursty Traffic

Research package for the manuscript *"Tail-Latency-Aware Segmented Waveguide-Enabled
Pinching-Antenna Systems for Hyper-Reliable Low-Latency Communications Under Bursty Traffic"*
(target venue: IEEE Transactions on Wireless Communications).

## Layout (follows Section 18 of the research guide)

| Path | Content |
|---|---|
| `02_Tail_Latency_Aware_SWAN_HRLLC_Bursty_Traffic.md` | The research execution guide (source of the plan). |
| `paper/main.tex`, `paper/refs.bib`, `paper/figures/` | IEEEtran manuscript and figures. Derivations assigned to the co-author are marked `[To do]`. |
| `src/arrivals.py` | ON–OFF (Markov-modulated), Poisson and periodic-with-jitter sources; closed-form tail-latency-aware required rate. |
| `src/queue.py` | Deadline-constrained FIFO queue as an age profile (ageing, dropping, FIFO service). |
| `src/swan_channel.py` | SWAN geometry, LoS channel with in-waveguide phase/attenuation, equal-gain aggregation, equal-SNR ZF with per-segment power. |
| `src/service.py` | Action table: SS/SA actions (aggregation depth $j$), SM actions, SNR, transmit power, active segments, FBL error tables. |
| `src/fbl.py` | Finite-blocklength normal approximation. |
| `src/tail_analysis.py` | Route-A tail analysis: effective bandwidth, effective capacity, QoS exponent, percentiles, CVaR. |
| `src/controller.py` | Proposed tail-aware controller (packet values, tail-risk potential, energy/configuration penalty, lookahead) and the weightings of the baselines. |
| `src/baselines.py` | Mapping of the guide's mandatory baselines to configurations. |
| `src/placement.py` | TAPP placement (block-coordinate descent) and benchmark placements. |
| `src/simulator.py` | Slot-level simulator (SimConfig, run_config). |
| `experiments/run_campaign.py` | Experiment definitions, resumable multiprocessing runner, pooling of results. |
| `experiments/plots.py`, `experiments/summarize.py` | Figures and text tables. |
| `tests/test_basic.py` | The unit tests of Section 19 of the guide (`python -m pytest -q tests`). |
| `results/` | Raw simulation outputs (one JSON per run). |
| `docs/` | Feasibility assessment (Vietnamese), research design, co-author hand-off. |

### Requirements
Python ≥ 3.10 with `numpy`, `scipy`, `matplotlib` (`pip install numpy scipy matplotlib`).

### Running
```bash
# quick smoke test (single configuration)
python -c "from src.simulator import SimConfig, run_config; print(run_config(SimConfig(T=20000))['pv'])"
python -m pytest -q tests

# all experiments (resumable; ~5 h on 4 cores), then figures
python -m experiments.run_campaign --procs 4
python -m experiments.run_campaign --exp bcd
python -m experiments.plots

# a subset, shorter runs
python -m experiments.run_campaign --exp peak burst --T-scale 0.4 --seeds 2
```

### Compiling the paper
```bash
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```
