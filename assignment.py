# assignment.py

from typing import List, Tuple


def picker_assignment(
    pallet_routes: List[List],
    pallet_distances: List[float],
    num_pickers: int
) -> Tuple[List[List[int]], float, List[float]]:
    """
    Assign pallets to pickers using a greedy LPT-like (Longest Processing Time) strategy.

    Inputs:
        pallet_routes:
            [
              ['Depot', i1, i2, ..., 'Depot'],  # route of pallet 1
              ['Depot', j1, j2, ..., 'Depot'],  # route of pallet 2
              ...
            ]
            (Route contents are not used in this function and are included for reference only.)

        pallet_distances:
            [
              total route distance of pallet 1,
              total route distance of pallet 2,
              ...
            ]

        num_pickers:
            Number of available pickers (int)

    Output:
        picker_assignments:
            [
              [pallet IDs assigned to picker 1],
              [pallet IDs assigned to picker 2],
              ...
            ]

        makespan:
            Maximum picker workload (total assigned distance)

        picker_loads:
            Total distance assigned to each picker (load list)
    """

    num_pallets = len(pallet_distances)
    if num_pallets == 0:
        return [[] for _ in range(num_pickers)], 0.0, [0.0 for _ in range(num_pickers)]

    # 1) Sort pallets in descending order of distance (LPT rule)
    pallets_with_dist = [
        (pallet_id, dist) for pallet_id, dist in enumerate(pallet_distances, start=1)
    ]
    pallets_with_dist.sort(key=lambda x: x[1], reverse=True)

    # 2) Initialize picker assignments and loads
    picker_assignments: List[List[int]] = [[] for _ in range(num_pickers)]
    picker_loads: List[float] = [0.0 for _ in range(num_pickers)]

    # 3) Assign each pallet to the picker with the minimum current load
    for pallet_id, dist in pallets_with_dist:
        min_picker_idx = min(range(num_pickers), key=lambda i: picker_loads[i])

        picker_assignments[min_picker_idx].append(pallet_id)
        picker_loads[min_picker_idx] += dist

    makespan = max(picker_loads) if picker_loads else 0.0

    return picker_assignments, makespan, picker_loads
