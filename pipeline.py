# pipeline.py

from typing import Dict, Any, Optional

from bblf import bblf
from data_loading import load_data, create_distance_matrices
from routing import pallet_route_calculation
from assignment import picker_assignment
from picker_timeline import build_picker_schedule, plot_picker_gantt
from debug_check import print_first_pallet_orders_and_items


def run_pipeline(
    items_file: str,
    orders_file: str,
    num_pickers: int,
    sheet_name: str = "Sheet1",
    debug: bool = False,
    visualize_pallets: bool = False,
    plot_gantt: bool = False,
    gantt_filename: Optional[str] = None,
    time_per_meter: float = 1.0,
) -> Dict[str, Any]:
    """
    Three-stage greedy initial-solution pipeline:

      1) Palletization: assign orders to pallets using BBLF
      2) Routing: compute a picking route and total distance for each pallet (Clarke–Wright)
      3) Assignment & scheduling: LPT-like picker assignment + timeline + (optional) Gantt chart

    Args:
        items_file:
            Excel file containing layout and item information (from resources).
        orders_file:
            Excel file containing order lists.
        num_pickers:
            Number of available pickers.
        sheet_name:
            Layout sheet name (used by create_distance_matrices).
        debug:
            Enable BBLF and general debug output.
        visualize_pallets:
            Whether to generate pallet visualization images.
        plot_gantt:
            Whether to plot a Gantt chart for the picker timeline.
        gantt_filename:
            Output filename for the Gantt chart (if None, only displayed).
        time_per_meter:
            Conversion factor from route distance to time units.

    Returns:
        A dictionary containing palletization, routing, assignment, and schedule outputs.
    """

    # 1) BBLF: pallet orders + detailed summary outputs
    pallet_orders, pallet_summary_df, pallets, order_pallet_mapping, failed_orders = bblf(
        items_file=items_file,
        orders_file=orders_file,
        debug=debug,
        visualize_pallets=visualize_pallets,
        return_summary=True,
    )

    # 2) Order -> item mapping (required for routing)
    items_dict, orders, orders_df = load_data(items_file, orders_file)

    # Debug helper: print detailed contents of the first pallet
    if debug:
        print_first_pallet_orders_and_items(
            pallets=pallets,
            order_pallet_mapping=order_pallet_mapping,
            orders=orders,
            items_dict=items_dict,
        )

    # 3) Distance matrices (derived from the layout file; aisle_length inferred automatically)
    item_item_dist, depot_dist_df = create_distance_matrices(
        excel_file=items_file,
        sheet_name=sheet_name,
    )

    # 4) Picking route and total distance for each pallet
    pallet_routes, pallet_distances = pallet_route_calculation(
        pallet_orders=pallet_orders,
        orders=orders,
        item_item_dist=item_item_dist,
        depot_dist_df=depot_dist_df,
    )

    # 5) Assign pallets to pickers (LPT-like)
    picker_assignments, makespan, picker_loads = picker_assignment(
        pallet_routes=pallet_routes,
        pallet_distances=pallet_distances,
        num_pickers=num_pickers,
    )

    # 6) Build picker timeline (sequential picking schedule)
    schedule_df = build_picker_schedule(
        picker_assignments=picker_assignments,
        pallet_distances=pallet_distances,
        time_per_meter=time_per_meter,
    )

    # 7) Optional Gantt chart
    if plot_gantt:
        plot_picker_gantt(
            schedule_df=schedule_df,
            show=True,
            filename=gantt_filename,
        )

    return {
        "pallet_orders": pallet_orders,
        "pallet_summary": pallet_summary_df,
        "pallet_routes": pallet_routes,
        "pallet_distances": pallet_distances,
        "picker_assignments": picker_assignments,
        "picker_loads": picker_loads,
        "makespan": makespan,
        "picker_schedule": schedule_df,
        "failed_orders": failed_orders,
    }
