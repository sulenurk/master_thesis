# routing.py

from typing import List, Dict, Tuple
import pandas as pd
from clarke_wright import ClarkeWrightSolver


def compute_route_distance(
    route: List,
    item_item_dist: pd.DataFrame,
    depot_dist_series: pd.Series
) -> float:
    """
    Compute the total distance of a picking route.

    Args:
        route:
            ['Depot', item1, item2, ..., 'Depot']
        item_item_dist:
            Item-to-item distance matrix (DataFrame with item IDs as index/columns).
        depot_dist_series:
            Series mapping item ID to depot distance.

    Returns:
        Total route distance.
    """
    # Remove depot nodes
    item_seq = [node for node in route if node != "Depot"]
    if not item_seq:
        return 0.0

    total = 0.0

    # Depot -> first item
    total += depot_dist_series[item_seq[0]]

    # Item -> item transitions
    for i in range(len(item_seq) - 1):
        total += item_item_dist.loc[item_seq[i], item_seq[i + 1]]

    # Last item -> depot
    total += depot_dist_series[item_seq[-1]]

    return total


def pallet_route_calculation(
    pallet_orders: List[List[int]],
    orders: Dict[int, List[int]],
    item_item_dist,
    depot_dist_df
) -> Tuple[List[List], List[float]]:
    """
    Compute picking routes and total distances for each pallet.

    Args:
        pallet_orders:
            Output of BBLF palletization:
            [
                [order_ids on pallet 1],
                [order_ids on pallet 2],
                ...
            ]
        orders:
            Mapping from order_id to list of item_ids.
        item_item_dist:
            Item-to-item distance matrix (DataFrame).
        depot_dist_df:
            DataFrame with columns ['Item ID', 'Depot_Distance'].

    Returns:
        pallet_routes:
            [
                ['Depot', i1, i2, ..., 'Depot'],  # route for pallet 1
                ['Depot', j1, j2, ..., 'Depot'],  # route for pallet 2
                ...
            ]
        pallet_distances:
            [
                total distance of pallet 1,
                total distance of pallet 2,
                ...
            ]
    """

    solver = ClarkeWrightSolver(item_item_dist, depot_dist_df)
    pallet_routes: List[List] = []
    pallet_distances: List[float] = []

    for pallet_idx, pallet_order_ids in enumerate(pallet_orders, start=1):
        # 1) Collect all items belonging to this pallet
        items_for_pallet: List[int] = []
        for order_id in pallet_order_ids:
            items_for_pallet.extend(orders[order_id])

        # 2) Compute route using the Clarke–Wright heuristic
        route = solver.solve(items_for_pallet)

        # 3) Compute route distance
        distance = compute_route_distance(
            route,
            item_item_dist=item_item_dist,
            depot_dist_series=solver.depot_dist
        )

        pallet_routes.append(route)
        pallet_distances.append(distance)

    return pallet_routes, pallet_distances
