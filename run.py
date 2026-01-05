# run.py

import os
import pandas as pd
import random
import numpy as np
import copy

from pipeline import run_pipeline
from sa_improvement_routing import (
    run_sa_improvement_makespan_and_assignment,
    run_sa_improvement_and_assignment,
)
from data_loading import load_data


# ===== PATHS AND FILE DEFINITIONS =====
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "resources")

ITEMS_FILE = os.path.join(RESOURCES_DIR, "10x90_warehouse_layout-item_list.xlsm")

ORDERS_FILES = [
    os.path.join(RESOURCES_DIR, "100_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "200_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "300_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "500_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "1000_order_list.xlsm"),
]

NUM_PICKERS_LIST = [2, 3, 5, 8]
SEED_LIST = [0, 1, 42, 1234, 10]


# ===== SA PARAMETERS =====
SA_CALL_PARAMS = {
    "T0": 50.0,
    "alpha": 0.99,
    "K": 30,
    "max_runtime_seconds": 600,
    "debug": False,
    "print_every": 200,
}


def safe_improvement_pct(base, new):
    base = float(base)
    new = float(new)
    if abs(base) < 1e-12:
        return "0.00%" if abs(new) < 1e-12 else "NA"
    return f"{round(((base - new) / base) * 100, 2)}%"


def main():
    results_rows = []

    # --- read parameters from a single source ---
    T0 = float(SA_CALL_PARAMS["T0"])
    alpha = float(SA_CALL_PARAMS["alpha"])
    K = int(SA_CALL_PARAMS["K"])
    MAX_RUNTIME_SECONDS = int(SA_CALL_PARAMS["max_runtime_seconds"])
    DEBUG = bool(SA_CALL_PARAMS["debug"])
    PRINT_EVERY = int(SA_CALL_PARAMS["print_every"])

    # param_id for reporting
    param_id = f"T0_{T0:g}_a_{alpha:g}_K_{K}"

    for orders_file in ORDERS_FILES:
        for num_pickers in NUM_PICKERS_LIST:

            print("\n" + "=" * 80)
            print("Running GREEDY + SA variants:")
            print(f"  orders_file = {os.path.basename(orders_file)}")
            print(f"  num_pickers = {num_pickers}")
            print(f"  param_id    = {param_id}")
            print("=" * 80)

            # ---------- GREEDY BASELINE ----------
            base_res = run_pipeline(
                items_file=ITEMS_FILE,
                orders_file=orders_file,
                num_pickers=num_pickers,
                debug=False,
                visualize_pallets=False,
                plot_gantt=False,
            )

            greedy_makespan = base_res["makespan"]
            initial_pallet_orders = base_res["pallet_orders"]

            orders_dict = base_res["orders"]
            item_item_dist = base_res["item_item_dist"]
            depot_dist_df = base_res["depot_dist_df"]

            items_dict, _, _ = load_data(ITEMS_FILE, orders_file)

            n_batches = len(initial_pallet_orders)
            dynamic_plateau = K * n_batches  # for reporting/logging only

            for seed in SEED_LIST:
                print(f"T0={T0} | alpha={alpha} | seed={seed} | K={K} | plateau_len={dynamic_plateau}")
                random.seed(seed)
                np.random.seed(seed)

                # ================= SA #1 (ROUTING objective + assignment) =================
                sa_res_1 = run_sa_improvement_and_assignment(
                    initial_pallet_orders=copy.deepcopy(initial_pallet_orders),
                    orders=orders_dict,
                    items_dict=items_dict,
                    item_item_dist=item_item_dist,
                    depot_dist_df=depot_dist_df,
                    num_pickers=num_pickers,
                    T0=T0,
                    alpha=alpha,
                    K=K,
                    max_runtime_seconds=MAX_RUNTIME_SECONDS,
                    debug=DEBUG,
                    print_every=PRINT_EVERY,
                    debug_makespan=False,
                )

                sa1_makespan = sa_res_1["makespan"]
                used_T0_1 = sa_res_1.get("T0", T0)

                sa1_stats = sa_res_1.get("sa_stats", {})
                sa1_runtime = sa1_stats.get("runtime_seconds", None)

                results_rows.append({
                    "orders_file": os.path.basename(orders_file),
                    "param_id": param_id,
                    "algo": "SA_routing",
                    "greedy_makespan": round(greedy_makespan, 2),
                    "improved_makespan": round(sa1_makespan, 2),
                    "improvement_abs": round(greedy_makespan - sa1_makespan, 2),
                    "improvement_pct": safe_improvement_pct(greedy_makespan, sa1_makespan),

                    "T0": used_T0_1,
                    "alpha": alpha,
                    "K_factor": K,
                    "n_batches": n_batches,
                    "plateau_length": dynamic_plateau,
                    "seed": seed,
                    "num_pickers": num_pickers,

                    # ✅ measured runtime
                    "runtime_seconds": sa1_runtime,

                    "iterations_used": sa1_stats.get("iterations_used", None),
                    "levels_completed": sa1_stats.get("levels_completed", None),
                    "stopping_condition": sa1_stats.get("stopped_reason", "completed"),
                })

                # ================= SA #2 (MAKESPAN objective + assignment) =================
                sa_res_2 = run_sa_improvement_makespan_and_assignment(
                    initial_pallet_orders=copy.deepcopy(initial_pallet_orders),
                    orders=orders_dict,
                    items_dict=items_dict,
                    item_item_dist=item_item_dist,
                    depot_dist_df=depot_dist_df,
                    num_pickers=num_pickers,
                    T0=T0,
                    alpha=alpha,
                    K=K,
                    max_runtime_seconds=MAX_RUNTIME_SECONDS,
                    debug=DEBUG,
                    print_every=PRINT_EVERY,
                )

                improved_makespan = sa_res_2["makespan"]
                improvement_abs = greedy_makespan - improved_makespan

                sa2_stats = sa_res_2.get("sa_stats", {})
                sa2_runtime = sa2_stats.get("runtime_seconds", None)

                results_rows.append({
                    "orders_file": os.path.basename(orders_file),
                    "param_id": param_id,
                    "algo": "SA_makespan",
                    "greedy_makespan": round(greedy_makespan, 2),
                    "improved_makespan": round(improved_makespan, 2),
                    "improvement_abs": round(improvement_abs, 2),
                    "improvement_pct": safe_improvement_pct(greedy_makespan, improved_makespan),

                    "T0": sa_res_2.get("T0", T0),
                    "alpha": alpha,
                    "K_factor": K,
                    "n_batches": n_batches,
                    "plateau_length": dynamic_plateau,
                    "seed": seed,
                    "num_pickers": num_pickers,

                    # ✅ measured runtime
                    "runtime_seconds": sa2_runtime,

                    "iterations_used": sa2_stats.get("iterations_used", None),
                    "levels_completed": sa2_stats.get("levels_completed", None),
                    "stopping_condition": sa2_stats.get("stopped_reason", "completed"),
                })

    # ================= SAVE TO EXCEL =================
    results_df = pd.DataFrame(results_rows)

    column_order = [
        "orders_file", "param_id", "algo", "num_pickers", "seed",
        "greedy_makespan", "improved_makespan", "improvement_abs", "improvement_pct",
        "runtime_seconds", "iterations_used", "levels_completed",
        "stopping_condition"
    ]

    final_columns = column_order + [c for c in results_df.columns if c not in column_order]

    out_path = os.path.join(PROJECT_ROOT, "FINAL_experiment_results.xlsx")
    results_df[final_columns].to_excel(out_path, index=False)
    print(f"\n[DONE] Results saved to: {out_path}")


if __name__ == "__main__":
    main()
