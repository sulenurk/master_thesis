# bblf.py

from typing import List, Tuple
from data_loading import load_data
from palletization import palletize_orders, generate_detailed_output
import pandas as pd


def bblf(
    items_file: str,
    orders_file: str,
    debug: bool = False,
    visualize_pallets: bool = False,
    output_dir: str = "pallet_visualizations",
    return_summary: bool = False
):
    """
    Wrapper function for BBLF-based palletization.

    Output (when return_summary=False):
        pallet_orders:
            [
                [order_ids assigned to pallet 1],
                [order_ids assigned to pallet 2],
                ...
            ]

    Output (when return_summary=True):
        (
            pallet_orders,
            pallet_summary_df,
            pallets,
            order_pallet_mapping,
            failed_orders
        )
    """

    # 1) Load input data
    items_dict, orders, orders_df = load_data(items_file, orders_file)

    # 2) Perform palletization
    pallets, order_pallet_mapping, failed_orders = palletize_orders(
        items_dict=items_dict,
        orders=orders,
        debug=debug,
        visualize=visualize_pallets,
        output_dir=output_dir
    )

    # 3) Build pallet → order list mapping
    num_pallets = len(pallets)
    pallet_orders: List[List[int]] = [[] for _ in range(num_pallets)]

    for order_id, pallet_id in order_pallet_mapping.items():
        pallet_orders[pallet_id - 1].append(order_id)

    for p in pallet_orders:
        p.sort()

    if not return_summary:
        return pallet_orders

    # 4) Generate detailed summary DataFrame
    pallet_summary_df = generate_detailed_output(
        pallets=pallets,
        orders_df=orders_df,
        order_pallet_mapping=order_pallet_mapping
    )

    return pallet_orders, pallet_summary_df, pallets, order_pallet_mapping, failed_orders
