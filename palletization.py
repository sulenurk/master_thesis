# palletization.py

import os
from tqdm import tqdm
from pallet import Pallet
from ems import EMS
import pandas as pd


def palletize_orders(
    items_dict,
    orders,
    debug: bool = False,
    visualize: bool = True,
    output_dir: str = "pallet_visualizations",
    debug_first_order: bool = False,
):
    """
    Attempt to place all items of each order into a single pallet.

    Args:
        items_dict:
            Mapping from Item ID to Item object.
        orders:
            Mapping from Order ID to list of Item IDs.
        debug:
            Whether to print general debug messages.
        visualize:
            Whether to generate final visualizations for each pallet.
        output_dir:
            Directory where pallet visualizations will be saved.
        debug_first_order:
            If True, print detailed debug output only for the first processed order.

    Returns:
        pallets:
            List of Pallet objects that were created/used.
        order_pallet_mapping:
            Mapping indicating which order was assigned to which pallet (Order ID -> Pallet ID).
        failed_orders:
            List of failed orders with the problematic item and a short reason.
    """
    pallets = []
    order_pallet_mapping = {}
    failed_orders = []

    # Create output directory for visualizations
    if visualize:
        os.makedirs(output_dir, exist_ok=True)

    # === SORT ORDERS BY TOTAL ITEM AREA (DESCENDING) ===
    def compute_order_total_area(item_ids):
        return sum(
            items_dict[item_id].length * items_dict[item_id].width
            for item_id in item_ids
        )

    # orders: dict (order_id -> item_id_list)
    # Sort (order_id, item_ids) pairs by total area
    sorted_orders = sorted(
        orders.items(),
        key=lambda kv: compute_order_total_area(kv[1]),
        reverse=True,
    )

    # Track the first order for detailed debugging (if requested)
    first_order_id = sorted_orders[0][0] if debug_first_order else None

    for order_id, item_ids in tqdm(sorted_orders, desc="Palletization"):
        if debug:
            print(f"\n=== Processing Order: {order_id} ===")
            print(f"Items: {item_ids}")

        # Prepare item copies for this order
        order_items = []
        for item_id in item_ids:
            it = items_dict[item_id].copy()
            it.order_id = order_id  # Store the order ID on the item
            order_items.append(it)

        # === SORT ITEMS WITHIN THE ORDER BY AREA (DESCENDING) ===
        order_items.sort(
            key=lambda it: it.length * it.width,
            reverse=True,
        )

        # Detailed debug output for the first order only
        if debug_first_order and order_id == first_order_id:
            print("\n[DEBUG] First order from orders dict:", order_id)
            print("       Item IDs:", item_ids)
            for iid in item_ids:
                it = items_dict[iid]
                print(f"       Item {iid} from items_dict -> {it.length}x{it.width}")

            print("\n[DEBUG] First order's order_items after copy():")
            for it in order_items:
                print(
                    f"       Item {it.item_id} in order_items -> "
                    f"{it.length}x{it.width}, rotated={it.rotated}"
                )

        placed = False

        # 1) Try placing the order into existing pallets
        for pallet in pallets:
            if debug:
                print(f"\n🔎 Trying Pallet {pallet.id}...")

            # Create a temporary pallet with copied EMS regions for feasibility checking
            temp_pallet = Pallet(pallet.id, pallet.length, pallet.width)
            temp_pallet.ems_list = [EMS(e.x, e.y, e.length, e.width) for e in pallet.ems_list]

            all_fit = all(temp_pallet.try_place_item(item.copy()) for item in order_items)

            if all_fit:
                if debug:
                    print(f"✅ Order {order_id}: all items fit in Pallet {pallet.id}.")
                for item in order_items:
                    pallet.try_place_item(item)
                order_pallet_mapping[order_id] = pallet.id
                placed = True
                break  # Pallet found for this order

        if placed:
            continue

        # 2) Create a new pallet
        new_pallet = Pallet(len(pallets) + 1)
        if debug:
            print(f"\n🆕 Created a new pallet: ID {new_pallet.id}")

        all_fit = True
        for item in order_items:
            if debug_first_order and order_id == first_order_id:
                print(f"\n[DEBUG] Placing item {item.item_id} of FIRST order on Pallet {new_pallet.id}")
                print(f"       BEFORE placement -> {item.length}x{item.width}, rotated={item.rotated}")

            if not new_pallet.try_place_item(item):
                all_fit = False
                failed_orders.append({
                    "Order ID": order_id,
                    "Failed Item": item.item_id,
                    "Reason": f"Minimum required space: {item.length}x{item.width}"
                })
                if debug:
                    print(f"❌ Item does not fit: {item.item_id} (Size: {item.length}x{item.width})")
                break

            if debug_first_order and order_id == first_order_id:
                placed_item = new_pallet.items[-1]
                print(f"       AFTER placement  -> {placed_item.length}x{placed_item.width}, rotated={placed_item.rotated}")
                print(f"       Stored at (x,y)=({placed_item.x},{placed_item.y})")

        if all_fit:
            pallets.append(new_pallet)
            order_pallet_mapping[order_id] = new_pallet.id
            if debug:
                print(f"✅ Order {order_id} → Pallet {new_pallet.id}")

    # Final visualization (all pallets)
    if visualize:
        for pallet in pallets:
            pallet.visualize(os.path.join(output_dir, f"final_pallet_{pallet.id}.png"))

    if debug:
        print("\n=== Placement Results ===")
        print(f"- Total number of pallets used: {len(pallets)}")
        print(f"- Number of failed orders: {len(failed_orders)}")

        if failed_orders:
            print("\n❌ Failed orders:")
            for fail in failed_orders:
                print(
                    f"  - Order {fail['Order ID']}, Item: {fail['Failed Item']}, "
                    f"Reason: {fail['Reason']}"
                )

    return pallets, order_pallet_mapping, failed_orders


def generate_detailed_output(pallets, orders_df, order_pallet_mapping):
    """
    Create a pallet-level summary DataFrame with:
      - Pallet ID
      - Orders (list)
      - Item Count
      - Utilization (%)
    """
    # Order → Pallet mapping table
    order_pallet_df = pd.DataFrame.from_dict(
        order_pallet_mapping,
        orient="index",
        columns=["Pallet ID"]
    ).reset_index()
    order_pallet_df = order_pallet_df.rename(columns={"index": "Order ID"})

    # Item count per order
    order_item_count = orders_df.groupby("Order ID").size().reset_index(name="Item Count")
    order_pallet_df = order_pallet_df.merge(order_item_count, on="Order ID")

    # Aggregate at pallet level
    pallet_orders_df = order_pallet_df.groupby("Pallet ID").agg({
        "Order ID": list,
        "Item Count": "sum"
    }).reset_index()

    # Add pallet utilization
    for pallet in pallets:
        utilization = pallet.occupied_area / (pallet.length * pallet.width) * 100
        pallet_orders_df.loc[
            pallet_orders_df["Pallet ID"] == pallet.id,
            "Utilization (%)"
        ] = utilization

    # Return sorted output
    return pallet_orders_df.sort_values("Pallet ID")
