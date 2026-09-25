# Research Execution Guide
## Tail-Latency-Aware SWAN for HRLLC With Bursty Industrial Traffic

### Target venue
- Primary: IEEE Transactions on Communications (TCOM)
- Alternative: IEEE Transactions on Wireless Communications (TWC)
- If the queueing theory is weak but one sharp tail result survives: IEEE Wireless Communications Letters.

## 1. Why this topic is kept
This topic is selected because it moves SWAN-HRLLC away from the increasingly crowded "maximize rate under finite blocklength" space.

The central scientific issue is:

> HRLLC packets fail not only because of poor instantaneous SNR, but because bursty arrivals, queueing, configuration delay, and short-packet decoding jointly create rare deadline violations.

PASS literature already contains tail-latency studies in federated learning. Therefore the novelty here must be specifically:
- packet-level HRLLC;
- bursty industrial arrivals;
- queue/service-process tail analysis;
- SWAN segment control;
- end-to-end deadline violation probability.

## 2. Core research question
How should a SWAN controller select segment mode, active segments, power, and service resources so that
\[
P(D_{\rm E2E}>D_{\max}\cup\mathcal E_{\rm dec})
\le \epsilon_{\max}
\]
under bursty, non-Poisson industrial traffic?

## 3. Research hypotheses
H1. Average delay can remain low while deep-tail deadline violation is unacceptable.

H2. Full-segment activation is not always optimal after configuration and service overhead are included.

H3. Queue-aware reliability control can reduce p99.999/p99.9999 latency at lower resource cost than rate-maximizing SWAN control.

H4. Bursty Markov arrivals materially change the optimal segment policy compared with i.i.d. arrivals.

## 4. Architecture
Use:
- one SWAN BS;
- \(M\) segments;
- one industrial HRLLC device initially;
- later optional two-class traffic.

Supported modes:
- segment selection (SS);
- segment aggregation (SA);
- optional segment multiplexing (SM) only if RF-chain cost is modeled.

## 5. Traffic model

### 5.1 Baseline Bernoulli arrivals
Use only for validation.

### 5.2 Markov-modulated arrivals
Preferred:
\[
S_t^{\rm arr}\in\{\text{OFF},\text{ON}\}.
\]

Transition matrix:
\[
\mathbf P_A=
\begin{bmatrix}
p_{00}&p_{01}\\
p_{10}&p_{11}
\end{bmatrix}.
\]

Packets per slot:
\[
A_t\sim
\begin{cases}
0, & \text{OFF},\\
\text{Bernoulli/Poisson burst}, & \text{ON}.
\end{cases}
\]

Control the:
- mean arrival rate;
- burst duration;
- peak/mean ratio.

### 5.3 Optional self-similar/heavy-tail sensitivity
Only after the Markov model is stable.

## 6. Queue model
Queue:
\[
Q_{t+1}
=
\max\{Q_t-S_t,0\}+A_t.
\]

\(S_t\) is successful packet service, which depends on:
- active segment mode;
- channel;
- FBL decoding;
- configuration time.

Packet delay:
\[
D=D_{\rm q}+D_{\rm cfg}+D_{\rm tx}+D_{\rm proc}.
\]

## 7. SWAN service model
For action
\[
a_t=(m_t,\mathcal S_t,\mathbf p_t,n_t),
\]
derive service rate or number of successfully served packets.

The model must include:
- waveguide attenuation;
- free-space propagation;
- segment-dependent SNR;
- segment activation/reconfiguration overhead.

## 8. FBL reliability
For each scheduled packet:
\[
\epsilon_t^{\rm dec}
\approx
Q\!\left(
\frac{C(\gamma_t)-B/n_t}
{\sqrt{V(\gamma_t)/n_t}}
\right).
\]

Effective packet service should account for decoding success.

## 9. Tail metrics
Primary:
\[
P(D>D_{\max}).
\]

Combined:
\[
\epsilon_{\rm E2E}
=
P(D>D_{\max}\cup\mathcal E_{\rm dec}).
\]

Also:
- p99;
- p99.9;
- p99.99;
- p99.999 latency;
- CVaR;
- mean delay only as a secondary metric.

## 10. Analytical route
At least one is required.

### Route A — Effective bandwidth/effective capacity
Arrival effective bandwidth:
\[
\alpha(\theta).
\]

Service effective capacity:
\[
\beta(\theta).
\]

Use the QoS exponent \(\theta\) to characterize tail decay.

### Route B — Stochastic network calculus
Obtain an upper bound
\[
P(D>D_{\max})\le \bar\epsilon(D_{\max}).
\]

### Route C — Large deviations
Derive an exponential approximation
\[
P(D>D_{\max})
\approx c\,e^{-\theta^\star D_{\max}}.
\]

The paper should compare analytical bound/approximation against simulation.

## 11. Optimization problem
Recommended:
\[
\min_\pi
\quad
\mathbb E[
c_{\rm energy}(a_t)
+c_{\rm cfg}(a_t)
]
\]
subject to
\[
P_\pi(D>D_{\max}\cup\mathcal E_{\rm dec})
\le \epsilon_{\max},
\]
\[
\bar Q<\infty.
\]

Alternative:
minimize CVaR delay plus energy.

## 12. Proposed controller
Start without DRL.

### Stage A
Offline evaluate each SWAN action:
- service distribution;
- energy cost;
- configuration delay.

### Stage B
Use queue state \(Q_t\), channel state, and current SWAN mode.

### Stage C
Define risk score:
\[
R_t(a)
=
\widehat P(D>D_{\max}|Q_t,\text{state},a).
\]

Choose minimum-cost feasible action:
\[
a_t^\star
=
\arg\min_a C(a)
\quad
\text{s.t. }R_t(a)\le\epsilon_{\rm slot}.
\]

### Optional Stage D
Use Lyapunov drift-plus-penalty if a clean queue-stability formulation is available.

### Optional Stage E
Only then evaluate PPO/DQN as a sequential baseline, not the scientific core.

## 13. Mandatory baselines
1. conventional PASS;
2. SWAN fixed SS;
3. SWAN fixed SA;
4. always-full-segment;
5. rate-maximizing controller;
6. average-delay-minimizing controller;
7. queue-aware non-tail controller;
8. proposed tail-aware controller.

## 14. Simulation settings
Suggested:
- \(M=2\)–8;
- payload 32–256 bits;
- slots 0.1–1 ms;
- deadlines 0.5–10 ms depending scenario;
- utilization from light to 0.95;
- ON-state persistence sweep;
- SNR range broad enough to expose service variation;
- reliability targets \(10^{-4}\)–\(10^{-7}\).

## 15. Mandatory figures
1. System + queue + SWAN service diagram.
2. Mean delay and tail delay versus traffic load.
3. CCDF of latency.
4. Deadline violation versus burst persistence.
5. Deadline violation versus number of segments.
6. Energy/resource cost versus reliability target.
7. SS/SA mode selection probability versus queue length.
8. Tail bound/approximation versus simulation.
9. Proposed versus rate-maximizing policy.
10. Sensitivity to configuration delay.

## 16. Key scientific figure
Plot:
\[
\text{mean delay}
\quad\text{and}\quad
P(D>D_{\max})
\]
for the same algorithms.

The paper should show that an algorithm can look good in average delay but fail HRLLC tail constraints.

## 17. Ablations
- Bernoulli vs bursty arrivals;
- no configuration delay;
- Shannon rate vs FBL;
- no waveguide loss;
- fixed SWAN mode;
- queue-blind action;
- tail-aware vs average-aware control.

## 18. Code structure
```text
swan_hrllc_tail/
├── configs/
├── src/
│   ├── arrivals.py
│   ├── queue.py
│   ├── swan_channel.py
│   ├── service.py
│   ├── fbl.py
│   ├── tail_analysis.py
│   ├── controller.py
│   └── baselines.py
├── experiments/
├── tests/
├── results/
└── figures/
```

## 19. Unit tests
1. Zero arrivals produce zero queue.
2. Service larger than queue cannot create negative queue.
3. Bernoulli arrival limit matches known mean-load behavior.
4. Increasing ON-state persistence increases burstiness at fixed mean.
5. FBL error decreases with SNR.
6. Zero configuration delay reproduces simplified service model.
7. Tail probability decreases with a larger deadline.
8. Analytical tail bound must not fall below observed probability if claimed as an upper bound.

## 20. Execution phases
Phase 0: literature audit on HRLLC tail latency, effective capacity, stochastic network calculus, PASS/SWAN.

Phase 1: queue + arrival validation.

Phase 2: SWAN physical service model.

Phase 3: FBL service process.

Phase 4: analytical tail model.

Phase 5: baseline controllers.

Phase 6: proposed risk-aware controller.

Phase 7: rare-tail simulation and confidence checks.

Phase 8: manuscript.

## 21. GO / NO-GO gate
Proceed to TCOM/TWC only if:
- burstiness changes the optimal policy materially;
- proposed method improves tail reliability, not only average delay;
- configuration overhead produces a genuine SWAN trade-off;
- at least one analytical tail expression/bound agrees with simulation;
- gains persist across multiple loads and burst parameters.

## 22. Expected contributions
1. A queueing-aware SWAN-HRLLC model with bursty industrial arrivals and FBL service.
2. An analytical characterization/bound of deadline-tail probability.
3. A tail-risk-aware SWAN segment/mode control method.
4. A demonstration that average-delay or rate optimization can violate HRLLC tail requirements.
5. Quantification of the cost of hyper-reliability under bursty traffic.

## 23. Positioning warning
Do not claim novelty for "tail latency" in general; PASS tail-latency work already exists in other applications.

The novelty must be:
\[
\boxed{
\text{bursty packet traffic}
+
\text{SWAN service dynamics}
+
\text{FBL}
+
\text{deadline-tail HRLLC control}
}
\]
