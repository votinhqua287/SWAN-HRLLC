"""Print pooled results of every experiment as text tables (for writing the paper)."""
import sys, numpy as np
from experiments.run_campaign import load, EXPERIMENTS


def fmt(v):
    return "inf" if (isinstance(v, float) and np.isinf(v)) else (f"{v:g}" if isinstance(v, (int, float)) else str(v))


def main(exps=None):
    exps = exps or list(EXPERIMENTS)
    for e in exps:
        try:
            R = load(e)
        except Exception as ex:
            print(e, "->", ex); continue
        if not R:
            print(f"== {e}: no results"); continue
        vals = sorted({v for s in R for v in R[s]}, key=lambda v: (v is None, v if not isinstance(v, str) else 0, str(v)))
        print(f"\n== {e} (param {EXPERIMENTS[e]['param']}) ==")
        head = "scheme".ljust(14) + "".join(fmt(v).rjust(11) for v in vals)
        print(head)
        for s in R:
            row = s.ljust(14)
            for v in vals:
                st = R[s].get(v)
                row += (f"{st['pv']:.2e}" if st else "-").rjust(11)
            print(row)
        if e in ("V",):
            for s in R:
                print("  power mW:", s, " ".join(f"{R[s][v]['power_mW']:.3f}" for v in vals))
        if e == "hetero":
            for s in R:
                for v in vals:
                    st = R[s][v]; print(f"  {s} {v}: crit={st['pv_crit']:.2e} reg={st['pv_reg']:.2e} worst={st['pv_worst']:.2e}")
        if e == "tau":
            for s in R:
                print("  reconf/run:", s, " ".join(f"{R[s][v]['reconf']:.0f}" for v in vals))
        # worst-user and counts
        for s in R:
            print("  n runs / viol:", s, " ".join(f"{R[s][v]['n']}/{int(R[s][v]['viol'])}" for v in vals))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
