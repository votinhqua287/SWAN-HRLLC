# Hand-off to the co-author: mathematical derivations and proofs

All items below are marked `[To do]` in `paper/main.tex` (search for `\todobox`). The
algorithms, the simulation code (`sim/`) and the numerical results are complete; what remains is
the formal justification of the statements below, written in the notation of the paper.
Priority order: **L1 → T1 → T2 → P1 → L2** (L1 and T1 are used in the text and the figures).

Notation reminder (Section II): $M$ segments, $K$ users, PA positions $\mathbf x$, per-segment
power $P_{\max}$, SA SNR $\gamma_k^{\rm SA}(\mathbf x,\rho)$ in (3), SM SNR in (4), FBL error
$\varepsilon(b,\gamma)$ in (5), ON–OFF source $(h_k,\alpha_k,\beta_k)$ [ON→OFF rate $\alpha$,
OFF→ON rate $\beta$, Poisson($h$) packets/slot in ON], tail target $(D_{\max},\delta_k)$,
required rate $c_{{\rm req},k}$ in (9), packet values $\nu_k(a)$, $v_k(a)$ and potential $\Phi$ in Sec. IV-C.

## L1 — Lemma 1 (tail-latency-aware required rate) — Appendix A
**Claim.** For the ON–OFF fluid source, $\mathrm{EB}(\theta)=\frac{1}{2\theta}[h\theta-\alpha-\beta+\sqrt{(h\theta-\alpha-\beta)^2+4\beta h\theta}]$;
the root of $\mathrm{EB}(\theta)=c$ is $\theta^\star(c)=\frac{(\alpha+\beta)c-\beta h}{c(h-c)}$ for
$\bar\lambda<c<h$; and imposing $\theta^\star(c)\,c\,D_{\max}\ge\ln(1/\delta)$ gives
$c_{\rm req}=h\frac{\beta+\Lambda}{\alpha+\beta+\Lambda}$, $\Lambda=\ln(1/\delta)/D_{\max}$.

**Suggested route.**
1. Effective bandwidth of a Markov fluid source: $\mathrm{EB}(\theta)=\frac1\theta\,\mathrm{sp}(\mathbf Q+\theta\mathbf H)$ with
   $\mathbf Q=\begin{pmatrix}-\beta&\beta\\ \alpha&-\alpha\end{pmatrix}$ (OFF, ON), $\mathbf H=\mathrm{diag}(0,h)$ (Kelly 1996; Elwalid–Mitra 1993).
   The characteristic polynomial gives the largest eigenvalue $\lambda_{\max}=\frac12[(\theta h-\alpha-\beta)+\sqrt{(\theta h-\alpha-\beta)^2+4\beta\theta h}]$.
2. Set $\lambda_{\max}=c\theta$; after dividing by $\theta$ one obtains the linear equation
   $c^2\theta-(\theta h-\alpha-\beta)c-\beta h=0$ in $\theta$, hence (8).
3. Large-buffer asymptotics (Chang 1994, Thm. on $\theta$-envelope rates; Anick–Mitra–Sondhi 1982 for the exact single-source result
   $\Pr\{W>w\}=A e^{-\theta^\star w}$ with $A=\Pr\{W>0\}<1$): $\Pr\{D>D_{\max}\}=\Pr\{W>cD_{\max}\}\le e^{-\theta^\star(c)cD_{\max}}$.
   Since $g(c)=\theta^\star(c)c=\frac{(\alpha+\beta)c-\beta h}{h-c}$ is increasing on $(\bar\lambda,h)$, the smallest $c$ with $g(c)\ge\Lambda$ is (9).
4. Comment on the discrete-time / Poisson-in-ON source used in the simulator: its effective bandwidth is
   $\frac1\theta\log\mathrm{sp}\big(\mathbf P\,\mathrm{diag}(1,e^{h(e^\theta-1)})\big)$ per slot (Chang 1994); show that (9) is a first-order approximation or give the exact counterpart.

## L2 — Lemma 2 (closed-form single-user placement) — Appendix B
**Claim.** If only user $k$ is active in the max-min objective, $x_m^\star=\Pi_{\mathcal X_m}(x_k-\zeta_m)$ where $\zeta_m\ge0$ solves a cubic (from
$\partial_{x_m}\big[e^{-2\alpha_g(x_m-(m-1)L_s)}/((x_k-x_m)^2+y_k^2+d^2)\big]=0$); with $\alpha_g=0$, $x_m^\star=\Pi_{\mathcal X_m}(x_k)$.
If two users share the active minimum, $x_m^\star$ is the root of the quadratic obtained from $\Gamma_k(\mathbf x)=\Gamma_j(\mathbf x)$
after using the monotonicity of $R^{\rm SA}$ in $\gamma$ and the fact that only the term $|h_{\cdot,m}|$ depends on $x_m$.
Give explicit coefficients; note the projection onto $\mathcal X_m$.

## P1 — Proposition 1 (convergence/complexity of TAPP) — Appendix C
Monotone non-decreasing objective (each block update is accepted only if it improves by more than $\xi$), bounded above by
$\max_k R_k^{\rm SA}/c_{{\rm req},k}$ at $r_{k,m}=d$, hence convergence; finite termination for $\xi>0$; $O(MGK)$ per sweep.
Optionally: any limit point of the continuous-domain version is a coordinate-wise maximizer, and discuss stationarity for the
max–min (non-smooth) objective (e.g., via Clarke stationarity).

## T1 — Theorem 1 (drift-plus-penalty characterisation of TAS) — Appendix D
**Objects.** Packet value $\nu_k(a)=e^{\kappa\Lambda_k(a-D_{\max})}$, $\Lambda_k=\ln(1/\delta_k)/D_{\max}$; potential
$\Phi=\sum_k\Phi_k$, $\Phi_k=\sum_a q_k[a]\nu_k(a)$; value delivered $U_k(b)=\sum_{i\le b}\nu_k(a_{k,(i)}+1)$.

**Dynamics (one slot).** Unserved packets: value $\times e^{\kappa\Lambda_k}$; arrivals: $+\nu_k(0)$ each (bounded by $A_{\max}$);
expiries: packets at age $D_{\max}-1$ that are not served leave with value $\nu_k(D_{\max}-1)=e^{-\kappa\Lambda_k}$ and are counted
as violations; delivered packets: $-U_k(b_k)$ w.p. $1-\varepsilon_k$.

**Claims.** (i) $\Delta(\Phi)+V\,\mathbb E[P_{\rm tot}]=C-\sum_{k\in\mathcal S}e^{\kappa\Lambda_k}(1-\varepsilon_k)U_k(b_k)+VP_{\rm tot}$ with $C$
action-independent ⇒ Algorithm 2 (with the constant $e^{\kappa\Lambda_k}$ absorbed in the values) is the exact per-slot minimiser of the
drift-plus-penalty expression. (ii) Under a slack condition (some stationary randomized policy removes value at a rate exceeding the
multiplicative growth by $\epsilon\Phi$ when $\Phi$ is large), the time average $\bar\Phi$ is bounded and
$P_k^{\rm v}\le e^{\kappa\Lambda_k}\bar\Phi_k/\bar\lambda_k$ (every discarded packet carried value $e^{-\kappa\Lambda_k}$ one slot earlier).
(iii) $O(1/V)$ energy optimality vs. $O(V)$ potential (penalty = energy $\sum_{m\in\mathcal A}(P_c+P_m^{\rm tx})T_s$ + configuration cost); the one-step lookahead term $\lambda\,\mathcal U^+(a)$ can be treated as a bounded perturbation of the per-slot objective.

**Suggested route.** Telescoping sum of the drift over $t=0..T-1$; compare the per-slot minimiser with the randomized policy $\pi$ at the same
state (the comparison is state-wise because (P3) minimises the exact conditional drift); Foster–Lyapunov type argument for the
multiplicative dynamics (see Neely 2010, Ch. 4, and Neely 2013 for delay-based potentials); express the slack through the SA rates
$R_k^{\rm SA}(\mathbf x^\star)$ and the required rates (Lemma 1) if possible. State all constants.

**Optional.** Relate the packet-value rule to the LWDF large-deviations optimality (Stolyar–Ramanan 2001): with a single packet per user the
rule reduces to LWDF with weights $\kappa\Lambda_k$.

## T2 — Theorem 2 (tail bound) — Appendix E
Effective-bandwidth/effective-capacity duality: $\Pr\{D_k>D_{\max}\}\le\varsigma_k e^{-\theta_k^\star\mathrm{EB}_k(\theta_k^\star)D_{\max}}$ where
$\theta_k^\star$ solves $\mathrm{EB}_k(\theta)=\mu_k(\theta)$ and $\mu_k(\theta)=-\lim\frac{1}{\theta t}\ln\mathbb E[e^{-\theta S_k(0,t)}]$
is the effective capacity of the service process under TLA-SWAN (Wu–Negi 2003; Chang 1994). FBL service model: in a slot in which
user $k$ is served with $b$ packets, $s_k=b$ w.p. $1-\varepsilon$ and $0$ otherwise (Gursoy 2013; Schiessl et al. 2018).
Lower bound on $\mu_k$: if user $k$ is in SA mode in a fraction $\phi_k$ of slots with bundle $b_k^{\rm SA}$ decoded w.p. $\ge1-\varepsilon_0$,
then by monotonicity of the effective capacity in the service distribution,
$\mu_k(\theta)\ge-\frac1\theta\ln\big(1-\phi_k+\phi_k(\varepsilon_0+(1-\varepsilon_0)e^{-\theta b_k^{\rm SA}})\big)$
(i.i.d. Bernoulli service as a stochastically smaller process). Discuss how to choose $\phi_k$ (e.g., $\phi_k=\min\{1,c_{{\rm req},k}/b_k^{\rm SA}\}$),
and produce the analytical curve for Fig. (ccdf) — the simulator already stores the per-user delay histograms in `results/ccdf/`.

## T3 (optional) — statistical vs. reactive reconfiguration
Show that reactive repositioning with silence $\tau_r$ per move cannot outperform the frame-level placement when
$\tau_r$ exceeds a threshold, by comparing effective throughputs $(1-\tau_r/T_{\rm move})R$; this explains Fig. (tau).

## Checklist before submission
- Replace every `\todobox{...}` in `paper/main.tex` with the proof or a pointer to the appendix.
- Verify every `% TODO verify` field in `paper/refs.bib` against the publisher page.
- Reconcile Section II with the original guide `02_Tail_Latency_Aware_SWAN_HRLLC_Bursty_Traffic.md`.
