"""Which runs belong to each experimental condition, and how to read them.

A repeated condition has five members: the original run and four with tiny boundary-layer offsets.
Every other condition has a single run, so its noise is not measured.
"""
import pandas as pd

REPEATED = ("t0", "ad_m2_sstup", "ad_m1_sstup", "ad_p1_sstup", "ad_p2_sstup", "ad_p1_sstfix", "ad_p2_sstfix", "q_p1_sstfix", "q_p2_sstfix")


def members(case):
    return [case] + [f"{case}_n{i}" for i in range(1, 5)] if case in REPEATED else [case]


def load_runs(results):
    return pd.read_csv(results / "run_summary_all.csv").set_index("case")


def load_energy(results):
    return pd.concat([pd.read_csv(results / "energy_summary.csv"), pd.read_csv(results / "energy_repeats.csv")]).set_index("case")
