"""Deadline-constrained FIFO queue kept as an age profile q[k, a] (packets of
user k with age a slots).  Ageing shifts the profile; packets reaching the drop
horizon are discarded; service removes the oldest packets first.
"""
import numpy as np


def fifo_remove(q, b):
    """Remove b[k] oldest packets from every row of q (K, H); returns served (K, H)."""
    rev = q[:, ::-1]
    cs = np.cumsum(rev, axis=1)
    before = cs - rev
    served_rev = np.clip(b[:, None] - before, 0, rev)
    return served_rev[:, ::-1]


def age_and_drop(q):
    """Age all packets by one slot; returns (q_new, dropped (K,))."""
    dropped = q[:, -1].copy()
    q_new = np.zeros_like(q)
    q_new[:, 1:] = q[:, :-1]
    return q_new, dropped


def hol_age(q):
    ages = np.arange(q.shape[1])[None, :]
    return np.max(np.where(q > 0, ages, -1), axis=1)
