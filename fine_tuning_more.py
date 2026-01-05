# run.py

import os
import pandas as pd
import random
import numpy as np
from itertools import product
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
    # os.path.join(RESOURCES_DIR, "100_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "200_order_list.xlsm"),
    # os.path.join(RESOURCES_DIR, "300_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "500_order_list.xlsm"),
    # os.path.join(RESOURCES_DIR, "1000_order_list.xlsm"),
]

NUM_PICKERS_LIST = [5]
SEED_LIST = [42]


# ===== PARAMETER GRIDS (TUNING) =====
T0_GRID = [50]          # Initial temperature values to tune
ALPHA_GRID = [0.99]
K_GRID = [30, 40, 50]   # Newly added K factor

# Stopping/plateau parameters (kept fixed; not part of tuning)
# PLATEAU_LEN = 800
# MAX_TOTAL_ITERS = 3000
MAX_RUNTIME_SECONDS = 600

DEBUG = False
PRINT_EVERY = 200


def main():
    results_rows = []

    for orders_file in ORDERS_FILES:
        for num_pickers in NUM_PICKERS_LIST:

            print("\n" + "=" * 80)
            print("Running GREEDY + SA variants with parameter tuning:")
            print(f"  orders_file = {os.path.basename(orders_file)}")
            print(f"  num_pickers = {num_pickers}")
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

            # ---------- PARAMETER GRID LOOP ----------
            for T0, alpha, K in product(T0_GRID, ALPHA_GRID, K_GRID):

                param_id = f"T0_{T0}_a{alpha}_K{K}"

                dynamic_plateau = K * n_batches

                for seed in SEED_LIST:
                    print(f"T0={T0} | alpha={alpha} | seed={seed} | K={K}")
                    random.seed(seed)
                    np.random.seed(seed)

                    """ # ================= SA #1 (ROUTING) =================
                    sa_res_1 = run_sa_improvement_and_assignment(
                        initial_pallet_orders=copy.deepcopy(initial_pallet_orders),
                        orders=orders_dict,
                        items_dict=items_dict,
                        item_item_dist=item_item_dist,
                        depot_dist_df=depot_dist_df,
                        num_pickers=num_pickers,
                        **SA_CALL_PARAMS
                    )

                    sa1_makespan = sa_res_1["makespan"]
                    used_T0_1 = sa_res_1["T0"]

                    results_rows.append({
                        "items_file": os.path.basename(ITEMS_FILE),
                        "orders_file": os.path.basename(orders_file),
                        "num_pickers": num_pickers,
                        "seed": seed,
                        "algo": "SA_routing",
                        "T0": used_T0_1,
                        "alpha": alpha,
                        "plateau_len": PLATEAU_LEN,
                        "max_runtime_seconds": MAX_RUNTIME_SECONDS,
                        "greedy_makespan": greedy_makespan,
                        "sa_makespan": sa1_makespan,
                        "improvement_abs": greedy_makespan - sa1_makespan,
                    }) """

                    # ================= SA #2 (MAKESPAN) =================
                    sa_res_2 = run_sa_improvement_makespan_and_assignment(
                        initial_pallet_orders=copy.deepcopy(initial_pallet_orders),
                        orders=orders_dict,
                        items_dict=items_dict,
                        item_item_dist=item_item_dist,
                        depot_dist_df=depot_dist_df,
                        num_pickers=num_pickers,
                        T0=T0,
                        alpha=alpha,
                        K=K,  # The function should compute L = K * n internally
                        max_runtime_seconds=MAX_RUNTIME_SECONDS,
                        debug=DEBUG,
                        print_every=PRINT_EVERY
                    )

                    improved_makespan = sa_res_2["makespan"]
                    improvement_abs = greedy_makespan - improved_makespan
                    improvement_pct = (improvement_abs / greedy_makespan) * 100

                    # Append results in the requested column layout
                    results_rows.append({
                        "orders_file": os.path.basename(orders_file),
                        "param_id": param_id,
                        "greedy_makespan": round(greedy_makespan, 2),
                        "improved_makespan": round(improved_makespan, 2),
                        "improvement_abs": round(improvement_abs, 2),
                        "improvement_pct": f"{round(improvement_pct, 2)}%",
                        "T0": T0,
                        "alpha": alpha,
                        "K_factor": K,
                        "n_batches": n_batches,
                        "plateau_length": dynamic_plateau,
                        "seed": seed,
                        "stopping_condition": sa_res_2.get("stopped_reason", "completed")
                    })

    # ================= SAVE TO EXCEL =================
    results_df = pd.DataFrame(results_rows)

    # Fix the column order
    column_order = [
        "orders_file", "param_id", "greedy_makespan", "improved_makespan",
        "improvement_abs", "improvement_pct", "stopping_condition"
    ]

    # Append remaining technical columns at the end
    final_columns = column_order + [c for c in results_df.columns if c not in column_order]

    out_path = os.path.join(PROJECT_ROOT, "grid_search_results_more.xlsx")
    results_df[final_columns].to_excel(out_path, index=False)
    print(f"\nGrid search completed. Output file saved to: {out_path}")


if __name__ == "__main__":
    main()
