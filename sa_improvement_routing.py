# =========================
# sa_improvement_routing.py
# =========================

import random
import copy
import math
from typing import Optional

from palletization import try_repack_single_batch
from clarke_wright import ClarkeWrightSolver
from routing import compute_route_distance, pallet_route_calculation
from assignment import picker_assignment


# ------------------------------------------------------------
# Neighborhood helper
# ------------------------------------------------------------
def swap_two_orders_between_batches(pallet_orders):
    """
    Randomly select two non-empty batches, pick one order from each, and swap them.

    Returns:
        (new_pallet_orders, b1, b2, o1, o2) or None if not possible.
    """
    new_pallet_orders = copy.deepcopy(pallet_orders)

    non_empty_batches = [i for i, b in enumerate(new_pallet_orders) if len(b) > 0]
    if len(non_empty_batches) < 2:
        return None

    b1, b2 = random.sample(non_empty_batches, 2)

    o1 = random.choice(new_pallet_orders[b1])
    o2 = random.choice(new_pallet_orders[b2])

    new_pallet_orders[b1].remove(o1)
    new_pallet_orders[b2].remove(o2)

    new_pallet_orders[b1].append(o2)
    new_pallet_orders[b2].append(o1)

    return new_pallet_orders, b1, b2, o1, o2


# =========================
# Debug helpers
# =========================
def _fmt_route(route):
    out = []
    for x in route:
        if isinstance(x, (tuple, list)) and len(x) > 0:
            out.append(str(x[0]))
        else:
            out.append(str(x))
    return " -> ".join(out)


def summarize_batches(routes, distances, max_show=10):
    lines = []
    n = len(distances)
    lines.append(f"Total batches: {n}, total distance: {sum(distances):.2f}")
    idx_sorted = sorted(range(n), key=lambda i: distances[i], reverse=True)
    for rank, i in enumerate(idx_sorted[:max_show], 1):
        lines.append(f"  #{rank:02d} b{i+1}: dist={distances[i]:.2f} | route={_fmt_route(routes[i])}")
    return "\n".join(lines)


def diff_batches(routes0, dist0, routes1, dist1, show=15, tol=1e-9):
    n = min(len(dist0), len(dist1))
    diffs = []
    for i in range(n):
        d = dist1[i] - dist0[i]
        route_changed = routes0[i] != routes1[i]
        if abs(d) > tol or route_changed:
            diffs.append((abs(d), i, d, route_changed))
    diffs.sort(reverse=True)

    lines = []
    lines.append(f"Changed batches: {len(diffs)}/{n}")
    for _, i, d, rc in diffs[:show]:
        lines.append(
            f"  b{i+1}: dist0={dist0[i]:.2f} -> dist1={dist1[i]:.2f} (Δ={d:+.2f}) | route_changed={rc}"
        )
        lines.append(f"    r0: {_fmt_route(routes0[i])}")
        lines.append(f"    r1: {_fmt_route(routes1[i])}")
    return "\n".join(lines)


# ============================================================
# SA 1: Routing-distance objective (pair distance)
# ============================================================
def simulated_annealing_batch_routing(
    initial_pallet_orders,
    orders,
    items_dict,
    item_item_dist,
    depot_dist_df,
    T0: float = 1.0,
    alpha: float = 0.97,
    K: int = 15,
    max_runtime_seconds: int = 600,
    debug: bool = False,
    print_every: int = 100,
    debug_makespan: bool = False,
    debug_num_pickers: int | None = None,
):
    import time

    stopped_reason = "unknown"
    start_time = time.time()

    n = len(initial_pallet_orders)
    plateau_len = K * n

    # ----- current solution -----
    current_orders = copy.deepcopy(initial_pallet_orders)
    current_routes, current_distances = pallet_route_calculation(
        current_orders, orders, item_item_dist, depot_dist_df
    )

    # ----- snapshots -----
    initial_orders_snapshot = copy.deepcopy(current_orders)
    initial_routes_snapshot = copy.deepcopy(current_routes)
    initial_distances_snapshot = copy.deepcopy(current_distances)

    solver = ClarkeWrightSolver(item_item_dist, depot_dist_df)

    T = float(T0)
    T0_used = float(T0)

    # ----- track best solution (FULL solution, not only scalar) -----
    current_total = float(sum(current_distances))
    best_total = current_total

    best_orders = copy.deepcopy(current_orders)
    best_routes = copy.deepcopy(current_routes)
    best_distances = copy.deepcopy(current_distances)

    if debug:
        print("\n" + "=" * 60)
        print("SA-ROUTING INITIAL STATE")
        print("=" * 60)
        print(f"Initial total route distance: {current_total:.2f}")
        print(f"Fixed T0: {T0_used:.6f}, alpha: {alpha}, plateau_len: {plateau_len}")
        print("=" * 60)
        print("INITIAL TOP BATCHES:")
        print(summarize_batches(current_routes, current_distances, max_show=10))
        print("=" * 60 + "\n")

    move_counter = 0
    level = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed >= max_runtime_seconds:
            stopped_reason = "time_limit"
            if debug:
                print(f"[STOP] time limit reached: {max_runtime_seconds}s")
            break

        level += 1
        improved_in_plateau = False

        for k in range(1, plateau_len + 1):
            elapsed = time.time() - start_time
            if elapsed >= max_runtime_seconds:
                stopped_reason = "time_limit"
                if debug:
                    print(f"[STOP] time limit reached: {max_runtime_seconds}s")

                stats = {
                    "iterations_used": move_counter,
                    "temp_final": T,
                    "runtime_seconds": elapsed,
                    "plateau_len": plateau_len,
                    "levels_completed": level,
                    "stopped_reason": stopped_reason,
                    "initial_orders": initial_orders_snapshot,
                    "initial_routes": initial_routes_snapshot,
                    "initial_distances": initial_distances_snapshot,
                    "best_total": best_total,
                    "final_total": float(sum(current_distances)),
                }
                return best_orders, best_routes, best_distances, T0_used, stats

            move_counter += 1

            neighbor = swap_two_orders_between_batches(current_orders)
            if neighbor is None:
                continue

            new_orders, b1, b2, o1, o2 = neighbor

            # Feasibility check (only affected batches)
            if not try_repack_single_batch(new_orders[b1], items_dict, orders):
                continue
            if not try_repack_single_batch(new_orders[b2], items_dict, orders):
                continue

            new_routes = copy.deepcopy(current_routes)
            new_distances = copy.deepcopy(current_distances)

            old_pair = current_distances[b1] + current_distances[b2]

            # Recompute route for b1
            items_b1 = []
            for oid in new_orders[b1]:
                items_b1.extend(orders[oid])
            route_b1 = solver.solve(items_b1)
            dist_b1 = compute_route_distance(route_b1, item_item_dist, solver.depot_dist)
            new_routes[b1] = route_b1
            new_distances[b1] = dist_b1

            # Recompute route for b2
            items_b2 = []
            for oid in new_orders[b2]:
                items_b2.extend(orders[oid])
            route_b2 = solver.solve(items_b2)
            dist_b2 = compute_route_distance(route_b2, item_item_dist, solver.depot_dist)
            new_routes[b2] = route_b2
            new_distances[b2] = dist_b2

            new_pair = dist_b1 + dist_b2
            delta = new_pair - old_pair

            old_total = float(sum(current_distances))
            new_total = old_total + delta

            # Metropolis acceptance
            if delta < 0:
                accepted = True
                reason = "ACCEPT (improved)"
            else:
                prob = math.exp(-delta / T) if T > 1e-12 else 0.0
                r = random.random()
                accepted = (r < prob)
                reason = f"{'ACCEPT' if accepted else 'REJECT'} (prob) p={prob:.4f}, r={r:.4f}"

            if debug and (move_counter % print_every == 0):
                print(
                    f"[lvl={level} k={k}/{plateau_len}] it={move_counter} T={T:.6f} "
                    f"swap b{b1+1}(o{o1}) ↔ b{b2+1}(o{o2}) "
                    f"pair: {old_pair:.2f}->{new_pair:.2f} Δpair={delta:+.2f} | "
                    f"total: {old_total:.2f}->{new_total:.2f} Δtotal={(new_total-old_total):+.2f} → {reason}"
                )

            if accepted:
                current_orders = new_orders
                current_routes = new_routes
                current_distances = new_distances

                if debug and (move_counter % print_every == 0):
                    print(f"  updated b{b1+1}: dist={current_distances[b1]:.2f} route={_fmt_route(current_routes[b1])}")
                    print(f"  updated b{b2+1}: dist={current_distances[b2]:.2f} route={_fmt_route(current_routes[b2])}")

                if debug_makespan and debug_num_pickers is not None and debug and (move_counter % print_every == 0):
                    _, ms, loads = picker_assignment(
                        pallet_routes=current_routes,
                        pallet_distances=current_distances,
                        num_pickers=debug_num_pickers
                    )
                    print(f"  makespan_now={ms:.2f} | loads={['{:.2f}'.format(x) for x in loads]}")

                current_total = float(sum(current_distances))
                if current_total < best_total - 1e-12:
                    best_total = current_total
                    best_orders = copy.deepcopy(current_orders)
                    best_routes = copy.deepcopy(current_routes)
                    best_distances = copy.deepcopy(current_distances)
                    improved_in_plateau = True

        if not improved_in_plateau:
            stopped_reason = "no_improvement_in_plateau"
            if debug:
                print(f"[STOP] no improvement during plateau at level={level}")
            break

        T *= alpha

    elapsed = time.time() - start_time

    if debug:
        print("\n[SA-ROUTING FINISHED]")
        print(f"  Best total route distance seen: {best_total:.2f}")
        print(f"  Final total route distance:     {float(sum(current_distances)):.2f}")
        print(f"  Total iterations: {move_counter}")
        print(f"  Final temperature: {T:.6f}")
        print(f"  Runtime: {elapsed:.1f}s")
        print(f"  Stopped reason: {stopped_reason}")

    stats = {
        "iterations_used": move_counter,
        "temp_final": T,
        "runtime_seconds": elapsed,
        "plateau_len": plateau_len,
        "levels_completed": level,
        "stopped_reason": stopped_reason,
        "initial_orders": initial_orders_snapshot,
        "initial_routes": initial_routes_snapshot,
        "initial_distances": initial_distances_snapshot,
        "best_total": best_total,
        "final_total": float(sum(current_distances)),
    }

    return best_orders, best_routes, best_distances, T0_used, stats


def run_sa_improvement_and_assignment(
    initial_pallet_orders,
    orders,
    items_dict,
    item_item_dist,
    depot_dist_df,
    num_pickers,
    T0: float = 1.0,
    alpha: float = 0.97,
    K: int = 15,  # Dynamic factor
    max_runtime_seconds: int = 600,
    debug: bool = False,
    print_every: int = 100,
    debug_makespan: bool = False,
):
    n = len(initial_pallet_orders)
    plateau_len = K * n

    # Initial snapshot (for debug comparison)
    init_routes, init_distances = pallet_route_calculation(
        copy.deepcopy(initial_pallet_orders), orders, item_item_dist, depot_dist_df
    )
    init_assign, init_ms, init_loads = picker_assignment(
        pallet_routes=init_routes,
        pallet_distances=init_distances,
        num_pickers=num_pickers
    )

    final_pallet_orders, final_routes, final_distances, T0_used, sa_stats = simulated_annealing_batch_routing(
        initial_pallet_orders=initial_pallet_orders,
        orders=orders,
        items_dict=items_dict,
        item_item_dist=item_item_dist,
        depot_dist_df=depot_dist_df,
        T0=T0,
        alpha=alpha,
        K=K,
        max_runtime_seconds=max_runtime_seconds,
        debug=debug,
        print_every=print_every,
        debug_makespan=debug_makespan,
        debug_num_pickers=num_pickers if debug_makespan else None,
    )

    picker_assignments, makespan, picker_loads = picker_assignment(
        pallet_routes=final_routes,
        pallet_distances=final_distances,
        num_pickers=num_pickers
    )

    if debug:
        print("\n" + "=" * 60)
        print("BATCH ROUTE COMPARISON: INITIAL vs FINAL (BEST SA output)")
        print("=" * 60)
        print("INITIAL SUMMARY:")
        print(summarize_batches(init_routes, init_distances, max_show=10))
        print("\nFINAL SUMMARY:")
        print(summarize_batches(final_routes, final_distances, max_show=10))
        print("\nDIFF (top changes):")
        print(diff_batches(init_routes, init_distances, final_routes, final_distances, show=10))
        print("=" * 60)

        print("\n" + "=" * 60)
        print("PICKER ASSIGNMENT COMPARISON: INITIAL vs FINAL (BEST SA output)")
        print("=" * 60)
        print(f"Initial makespan: {init_ms:.2f} | loads={['{:.2f}'.format(x) for x in init_loads]}")
        print(f"Final makespan:   {makespan:.2f} | loads={['{:.2f}'.format(x) for x in picker_loads]}")
        print("=" * 60 + "\n")

    return {
        "final_pallet_orders": final_pallet_orders,
        "final_routes": final_routes,
        "final_distances": final_distances,
        "picker_assignments": picker_assignments,
        "picker_loads": picker_loads,
        "makespan": makespan,
        "T0": T0_used,
        "sa_stats": sa_stats,
        "initial_routes": init_routes,
        "initial_distances": init_distances,
        "initial_picker_assignments": init_assign,
        "initial_makespan": init_ms,
        "initial_picker_loads": init_loads,
    }


# ------------------------------------------------------------
# SA 2: Makespan objective
# ------------------------------------------------------------
def simulated_annealing_batch_makespan(
    initial_pallet_orders,
    orders,
    items_dict,
    item_item_dist,
    depot_dist_df,
    num_pickers: int,
    T0: float = 1.0,
    alpha: float = 0.97,
    K: int = 15,
    max_runtime_seconds: int = 600,
    debug: bool = False,
    print_every: int = 100,
):
    import time

    start_time = time.time()
    stopped_reason = "unknown"

    n = len(initial_pallet_orders)
    plateau_len = K * n

    current_orders = copy.deepcopy(initial_pallet_orders)
    current_routes, current_distances = pallet_route_calculation(
        current_orders, orders, item_item_dist, depot_dist_df
    )
    current_picker_assignments, current_makespan, current_picker_loads = picker_assignment(
        pallet_routes=current_routes,
        pallet_distances=current_distances,
        num_pickers=num_pickers,
    )

    best_orders = copy.deepcopy(current_orders)
    best_routes = copy.deepcopy(current_routes)
    best_distances = copy.deepcopy(current_distances)
    best_picker_assignments = copy.deepcopy(current_picker_assignments)
    best_picker_loads = copy.deepcopy(current_picker_loads)
    best_makespan = float(current_makespan)

    solver = ClarkeWrightSolver(item_item_dist, depot_dist_df)

    T = float(T0)
    T0_used = float(T0)

    if debug:
        print("\n" + "=" * 60)
        print("SA-MAKESPAN INITIAL STATE")
        print("=" * 60)
        print(f"Initial makespan: {current_makespan:.2f}")
        print(f"Fixed T0: {T0_used:.6f}, alpha: {alpha}, plateau_len: {plateau_len}")
        print("=" * 60 + "\n")

    move_counter = 0
    level = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed >= max_runtime_seconds:
            stopped_reason = "time_limit"
            if debug:
                print(f"[STOP] time limit reached: {max_runtime_seconds}s")
            break

        level += 1
        improved_in_plateau = False

        for k in range(1, plateau_len + 1):
            elapsed = time.time() - start_time

            if elapsed >= max_runtime_seconds:
                stopped_reason = "time_limit"
                if debug:
                    print(f"[STOP] time limit reached: {max_runtime_seconds}s")

                sa_stats = {
                    "iterations_used": move_counter,
                    "temp_final": T,
                    "runtime_seconds": elapsed,
                    "plateau_len": plateau_len,
                    "levels_completed": level,
                    "stopped_reason": stopped_reason,
                }
                return (
                    best_orders,
                    best_routes,
                    best_distances,
                    best_picker_assignments,
                    best_picker_loads,
                    best_makespan,
                    T0_used,
                    sa_stats,
                )

            move_counter += 1

            neighbor = swap_two_orders_between_batches(current_orders)
            if neighbor is None:
                continue

            new_orders, b1, b2, o1, o2 = neighbor

            if not try_repack_single_batch(new_orders[b1], items_dict, orders):
                continue
            if not try_repack_single_batch(new_orders[b2], items_dict, orders):
                continue

            new_routes = copy.deepcopy(current_routes)
            new_distances = copy.deepcopy(current_distances)

            items_b1 = []
            for oid in new_orders[b1]:
                items_b1.extend(orders[oid])
            route_b1 = solver.solve(items_b1)
            dist_b1 = compute_route_distance(route_b1, item_item_dist, solver.depot_dist)
            new_routes[b1] = route_b1
            new_distances[b1] = dist_b1

            items_b2 = []
            for oid in new_orders[b2]:
                items_b2.extend(orders[oid])
            route_b2 = solver.solve(items_b2)
            dist_b2 = compute_route_distance(route_b2, item_item_dist, solver.depot_dist)
            new_routes[b2] = route_b2
            new_distances[b2] = dist_b2

            new_picker_assignments, new_makespan, new_picker_loads = picker_assignment(
                pallet_routes=new_routes,
                pallet_distances=new_distances,
                num_pickers=num_pickers,
            )

            delta = float(new_makespan - current_makespan)

            if delta < 0:
                accepted = True
                reason = "ACCEPT (improved)"
            else:
                prob = math.exp(-delta / T) if T > 1e-12 else 0.0
                r = random.random()
                accepted = (r < prob)
                reason = f"{'ACCEPT' if accepted else 'REJECT'} (prob) p={prob:.4f}, r={r:.4f}"

            if debug and (move_counter % print_every == 0):
                print(
                    f"[lvl={level} k={k}/{plateau_len}] it={move_counter} T={T:.6f} "
                    f"swap b{b1+1}(o{o1}) ↔ b{b2+1}(o{o2}) "
                    f"mksp {current_makespan:.2f}→{new_makespan:.2f} Δ={delta:.2f} → {reason}"
                )

            if accepted:
                current_orders = new_orders
                current_routes = new_routes
                current_distances = new_distances
                current_picker_assignments = new_picker_assignments
                current_picker_loads = new_picker_loads
                current_makespan = float(new_makespan)

                if current_makespan < best_makespan - 1e-12:
                    best_makespan = current_makespan
                    best_orders = copy.deepcopy(current_orders)
                    best_routes = copy.deepcopy(current_routes)
                    best_distances = copy.deepcopy(current_distances)
                    best_picker_assignments = copy.deepcopy(current_picker_assignments)
                    best_picker_loads = copy.deepcopy(current_picker_loads)
                    improved_in_plateau = True

        if not improved_in_plateau:
            stopped_reason = "no_improvement_in_plateau"
            if debug:
                print(f"[STOP] no improvement during plateau at level={level}")
            break

        T *= alpha

    elapsed = time.time() - start_time

    if debug:
        print("\n[SA-MAKESPAN FINISHED]")
        print(f"  Best makespan: {best_makespan:.2f}")
        print(f"  Best picker loads: {best_picker_loads}")
        print(f"  Total iterations: {move_counter}")
        print(f"  Final temperature: {T:.6f}")
        print(f"  Runtime: {elapsed:.1f}s")
        print(f"  Stopped reason: {stopped_reason}")

    sa_stats = {
        "iterations_used": move_counter,
        "temp_final": T,
        "runtime_seconds": elapsed,
        "plateau_len": plateau_len,
        "levels_completed": level,
        "stopped_reason": stopped_reason,
    }

    return (
        best_orders,
        best_routes,
        best_distances,
        best_picker_assignments,
        best_picker_loads,
        best_makespan,
        T0_used,
        sa_stats,
    )


def run_sa_improvement_makespan_and_assignment(
    initial_pallet_orders,
    orders,
    items_dict,
    item_item_dist,
    depot_dist_df,
    num_pickers,
    T0: float = 1.0,
    alpha: float = 0.97,
    K: int = 15,
    max_runtime_seconds: int = 600,
    debug: bool = False,
    print_every: int = 100,
):
    (
        best_orders,
        best_routes,
        best_distances,
        best_picker_assignments,
        best_picker_loads,
        best_makespan,
        T0_used,
        sa_stats
    ) = simulated_annealing_batch_makespan(
        initial_pallet_orders=initial_pallet_orders,
        orders=orders,
        items_dict=items_dict,
        item_item_dist=item_item_dist,
        depot_dist_df=depot_dist_df,
        num_pickers=num_pickers,
        T0=T0,
        alpha=alpha,
        K=K,
        max_runtime_seconds=max_runtime_seconds,
        debug=debug,
        print_every=print_every,
    )

    return {
        "final_pallet_orders": best_orders,
        "final_routes": best_routes,
        "final_distances": best_distances,
        "picker_assignments": best_picker_assignments,
        "picker_loads": best_picker_loads,
        "makespan": best_makespan,
        "T0": T0_used,
        "sa_stats": sa_stats,
    }
