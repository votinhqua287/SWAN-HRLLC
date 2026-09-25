# Research design: Tail-Latency-Aware SWAN for HRLLC under Bursty Traffic

This document is the single source of truth for the model, the problem, the proposed
scheme and the experiments implemented in `sim/` and written up in `paper/main.tex`.
It was reconstructed from the title of the (inaccessible) guide
`02_Tail_Latency_Aware_SWAN_HRLLC_Bursty_Traffic.md` and from the literature; reconcile it
with the guide before submission.

## 1. System model (downlink SWAN)

* **Geometry.** $M$ waveguide segments of length $L_s$ placed end-to-end along the $x$-axis at
  height $d$; segment $m$ spans $[(m-1)L_s, mL_s]$, feed point at its left end
  $\boldsymbol\psi_m^0=[(m-1)L_s,0,d]$ (Ouyang et al., TCOM 2026). One pinching antenna (PA) is
  activated per segment at $x_m\in[(m-1)L_s+\epsilon_x,\, mL_s-\epsilon_x]$. Each feed is driven by
  its own RF chain and power amplifier (budget $P_{\max}$ per segment). $K$ single-antenna users at
  $\mathbf u_k=[x_k,y_k,0]$, uniform in $[0,ML_s]\times[-D_y/2,D_y/2]$, static over a frame.
* **Channel.** $h_{k,m}(x_m)=\frac{\sqrt\eta\,e^{-\alpha\ell_m}}{r_{k,m}}\exp\{-\mathrm j\frac{2\pi}{\lambda}(r_{k,m}+n_{\rm eff}\ell_m)\}$,
  $\ell_m=x_m-(m-1)L_s$, $r_{k,m}=\sqrt{(x_k-x_m)^2+y_k^2+d^2}$, $\eta=c^2/(16\pi^2f_c^2)$,
  $\alpha=\kappa\ln 10/20$ ($\kappa$ in dB/m). Optional Rician small-scale fading (robustness only).
  $\mathbf h_k(\mathbf x)=[h_{k,1},\dots,h_{k,M}]^{\rm T}$.
* **Two operating modes per slot** (digital precoding across segment feeds):
  * *Segment aggregation (SA)* for a single scheduled user: equal-gain transmission, every
    segment at full power with phase alignment, $\gamma_k^{\rm SA}=P_{\max}(\sum_m|h_{k,m}|)^2/\sigma^2$.
  * *Segment multiplexing (SM)* for a set $\mathcal S$ ($|\mathcal S|\le M$): equal-SNR zero-forcing
    $\mathbf W=\mathbf H_{\mathcal S}^{\rm H}(\mathbf H_{\mathcal S}\mathbf H_{\mathcal S}^{\rm H})^{-1}$, common
    power $p(\mathcal S)=P_{\max}/\max_m\sum_{j\in\mathcal S}|w_{m,j}|^2$ (per-segment power
    constraint), $\gamma_j=\rho\,p(\mathcal S)/\sigma^2$ with power-control factor $\rho\in(0,1]$.
* **Slots and finite blocklength.** Slot $T_s=0.1$ ms, $n=200$ channel uses (2 MHz). A user
  scheduled with $b$ packets of $L$ bits uses rate $R=bL/n$ and fails with probability
  $\varepsilon(b,\gamma)=Q\big((C(\gamma)-R+\tfrac{\log_2 n}{2n})\sqrt{n/V(\gamma)}\big)$,
  $C=\log_2(1+\gamma)$, $V=(1-(1+\gamma)^{-2})\log_2^2e$. Failure ⇒ packets stay in the queue.
* **Bursty traffic.** Per user an ON–OFF Markov source: ON→OFF rate $\alpha_k$, OFF→ON rate
  $\beta_k$, Poisson($h_k$) packets per slot in ON, none in OFF; mean rate $\bar\lambda_k=h_k\beta_k/(\alpha_k+\beta_k)$.
  Two classes: regular and critical (larger $h$, tighter $\delta$). Alternatives for robustness:
  Poisson, periodic-with-jitter + event bursts.
* **Queue and tail metric.** FIFO per user, packet age tracked in slots; packets older than
  $D_{\max}$ are discarded (deadline dropping). Delay $D$ = arrival→successful delivery.
  HRLLC constraint $\Pr\{D_k>D_{\max}\}\le\delta_k$; violation = late or dropped.
* **Reconfiguration delay.** Changing the activated PA position of a segment silences it for
  $\tau_r$ slots. The proposed scheme reconfigures only at frame boundaries; the reactive
  benchmark pays $\tau_r$ each time it moves.

## 2. Problem formulation

$$\min_{\{\mathbf x[f]\},\{\mathcal S[t],\mathbf b[t],\rho[t]\}}\ \max_k\ \Pr\{D_k>D_{\max}\}\quad
\text{s.t. } x_m\in\mathcal X_m,\ \text{per-segment power},\ |\mathcal S[t]|\le M,\ \text{FBL success model}.$$
Equivalent "power-minimisation under tail constraints" form used for the drift-plus-penalty
derivation: minimise the long-term average transmit power s.t. $\Pr\{D_k>D_{\max}\}\le\delta_k$.
The delay-violation probability has no closed form under scheduling; the scheme works with
(i) a statistical surrogate at the frame level and (ii) virtual queues + packet values at the slot level.

## 3. Proposed scheme: TLA-SWAN (two timescales)

### 3.1 Tail-latency-aware required rate (Lemma, colleague)
For an ON–OFF fluid source the large-buffer asymptotics give
$\Pr\{D>D_{\max}\}\approx e^{-\theta^*(c)\,c\,D_{\max}}$, $\theta^*(c)=\frac{(\alpha+\beta)c-\beta h}{c(h-c)}$,
hence the smallest constant service rate meeting $\delta$ is
$$c_{\rm req}=h\,\frac{\beta+\Lambda}{\alpha+\beta+\Lambda},\qquad \Lambda=\frac{\ln(1/\delta)}{D_{\max}}.$$
($\Lambda\to0$: mean rate; $\Lambda\to\infty$: peak rate.) Implemented in `traffic.required_rate_onoff`.

### 3.2 Algorithm 1 — Tail-Aware PA Placement (TAPP), frame level
Maximise the minimum tail-latency margin $\min_k R_k^{\rm SA}(\mathbf x)/c_{{\rm req},k}$, where
$R_k^{\rm SA}$ is the FBL rate (packets/slot) of user $k$ in aggregation mode. Block-coordinate
descent over segments, each block solved by a 1-D grid search (G points) on $\mathcal X_m$;
stop when no block improves. Complexity $O(I\,M\,G\,K)$. Outputs $\mathbf x^\star$ per frame.
Benchmarks: sum-rate placement, tail-agnostic max-min rate, nearest-user projection, segment centres.

### 3.3 Algorithm 2 — Tail-Aware Scheduling with packet values (TAS), slot level
State: age profile $q_k[a]$, virtual credit $Z_k$ (packets), power level set $\{\rho_i\}$.
1. Credit update (ε-persistent virtual queue): $Z_k\leftarrow\min\{\max\{Z_k+c_{{\rm req},k}\mathbb 1\{Q_k>0\}-s_k,0\},Z_k^{\max}\}$.
2. Packet value of a packet of user $k$ with age $a$: $v_k(a)=\exp\{a_k(a+1+\zeta Z_k/c_{{\rm req},k}-D_{\max})\}$,
   $a_k=\ln(1/\delta_k)/D_{\max}$ (exponential/LWDF-type tail weight, shifted by the credit).
   $U_k(b)$ = value of the $b$ oldest packets.
3. For every subset $\mathcal S$ and power level $\rho$ (tables precomputed once per frame):
   $b_k^\star=\arg\max_b (1-\varepsilon_k(b,\rho\gamma(\mathcal S)))U_k(b)$;
   $J(\mathcal S,\rho)=\sum_{k\in\mathcal S}(1-\varepsilon_k(b_k^\star))U_k(b_k^\star)-V\rho P_{\rm tot}(\mathcal S)$.
   Choose $\arg\max J$ (exhaustive for $K\le 12$, greedy otherwise). $|\mathcal S|=1$ ⇒ SA mode.
4. Transmit, ARQ on failure, drop expired packets.
Theorems (colleague): drift-plus-penalty bound and bounded virtual queues ⇒ worst-case delay bound;
EC/SNC-based tail bound for the resulting service process.

## 4. Benchmarks
| Tag | Placement | Scheduler | Purpose |
|---|---|---|---|
| TLA-SWAN | TAPP | TAS | proposed |
| SWAN-MLWDF | TAPP | M-LWDF | classic tail-aware scheduler |
| SWAN-MW | TAPP | max-weight (queue length) | throughput-optimal, tail-agnostic |
| SWAN-EDF | TAPP | earliest deadline first | deadline-aware, channel-agnostic |
| SWAN-SR | sum-rate | max-weight | rate-centric SWAN |
| SWAN-fixed | segment centres | TAS | no PA reconfiguration |
| SWAN-reactive | per-slot chasing, delay $\tau_r$ | TAS | reactive repositioning |
| PASS-1WG | single long waveguide, 1 RF chain (SA/TDMA only) | TAS | value of segmentation |
| Fixed array | $M$ co-located antennas at the centre | TAS | value of pinching |

## 5. Experiments (`sim/experiments.py`)
E1 delay CCDF; E2 vs peak rate $h$; E3 vs burst length $1/\alpha$; E4 vs $P_{\max}$; E5 vs $M$;
E6 vs $D_{\max}$; E7 vs $K$; E8 vs $\tau_r$ (reactive vs proposed); E9 power–tail trade-off vs $V$;
E10 heterogeneous classes (placement comparison); E11 BCD convergence; E12 robustness (Rician,
$c_{\rm req}$ mismatch, traffic model). Default: $M=4$, $L_s=10$ m, $d=3$ m, $D_y=10$ m, $K=8$,
$f_c=28$ GHz, $n_{\rm eff}=1.4$, $\kappa=0.08$ dB/m, $\sigma^2=-101$ dBm, $P_{\max}=-10$ dBm,
$L=256$ bits, $D_{\max}=1$ ms, $\delta=10^{-5}$, ON 1 ms / OFF 9 ms, $h=3$ packets/slot.
