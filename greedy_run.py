# run_experiments_greedy.py

import os
import pandas as pd
from pipeline import run_pipeline
import time

# =======================
# PATHS
# =======================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "resources")

ITEMS_FILE = os.path.join(RESOURCES_DIR, "10x90_warehouse_layout-item_list.xlsm")

# Five order files
ORDERS_FILES = [
    os.path.join(RESOURCES_DIR, "100_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "200_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "300_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "500_order_list.xlsm"),
    os.path.join(RESOURCES_DIR, "1000_order_list.xlsm"),
]

NUM_PICKERS_LIST = [2, 3, 5, 8]

DUMP_PALLET_ORDER_LISTS = True
DUMP_DIR = os.path.join(PROJECT_ROOT, "greedy_pallet_order_lists")


def safe_mean_utilization(pallet_summary):
    """
    Return the mean pallet utilization (%) if available in pallet_summary.
    Otherwise, return None.
    """
    if pallet_summary is None:
        return None
    if hasattr(pallet_summary, "columns") and "Utilization (%)" in pallet_summary.columns:
        return float(pallet_summary["Utilization (%)"].mean())
    return None


def dump_pallet_orders_txt(out_txt_path, pallet_orders):
    """
    Write pallet-to-order assignments to a text file.
    """
    os.makedirs(os.path.dirname(out_txt_path), exist_ok=True)
    with open(out_txt_path, "w", encoding="utf-8") as f:
        for pallet_idx, order_list in enumerate(pallet_orders, start=1):
            f.write(f"Pallet {pallet_idx}: {order_list}\n")


def main():
    if DUMP_PALLET_ORDER_LISTS:
        os.makedirs(DUMP_DIR, exist_ok=True)

    results_rows = []

    for orders_file in ORDERS_FILES:
        orders_basename = os.path.basename(orders_file)

        for num_pickers in NUM_PICKERS_LIST:
            print("=" * 80)
            print(f"GREEDY | orders={orders_basename} | pickers={num_pickers}")
            print("=" * 80)

            t0 = time.perf_counter()
            res = run_pipeline(
                items_file=ITEMS_FILE,
                orders_file=orders_file,
                num_pickers=num_pickers,
                debug=False,
                visualize_pallets=False,   # set to True if visualization is needed (may slow down execution)
                plot_gantt=False,
            )

            runtime_seconds = time.perf_counter() - t0

            pallet_orders = res.get("pallet_orders", [])
            pallet_distances = res.get("pallet_distances", [])
            failed_orders = res.get("failed_orders", [])
            pallet_summary = res.get("pallet_summary", None)

            avg_util = safe_mean_utilization(pallet_summary)

            makespan = float(res.get("makespan", 0.0))
            total_distance = float(sum(pallet_distances)) if pallet_distances else 0.0

            results_rows.append({
                "items_file": os.path.basename(ITEMS_FILE),
                "orders_file": orders_basename,
                "num_pickers": num_pickers,
                "makespan": makespan,
                "total_distance": total_distance,
                "num_pallets": len(pallet_orders),
                "num_failed_orders": len(failed_orders),
                "avg_utilization": avg_util,
                "runtime_seconds": runtime_seconds,
            })

            # Dump pallet → order lists to text files
            if DUMP_PALLET_ORDER_LISTS:
                out_txt = os.path.join(
                    DUMP_DIR,
                    f"pallet_orders__{os.path.splitext(orders_basename)[0]}__pickers_{num_pickers}.txt"
                )
                dump_pallet_orders_txt(out_txt, pallet_orders)

    # =======================
    # SAVE RESULTS
    # =======================
    results_df = pd.DataFrame(results_rows)

    # Fix column order
    col_order = [
        "items_file", "orders_file", "num_pickers",
        "makespan", "total_distance", "num_pallets",
        "num_failed_orders", "avg_utilization",
        "runtime_seconds",
    ]
    results_df = results_df[col_order]

    out_xlsx = os.path.join(PROJECT_ROOT, "greedy_results.xlsx")
    results_df.to_excel(out_xlsx, index=False)

    print("\n[DONE] Saved to:", out_xlsx)
    print(results_df)


if __name__ == "__main__":
    main()
