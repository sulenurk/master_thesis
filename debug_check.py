# debug_check.py

def print_first_pallet_orders_and_items(pallets, order_pallet_mapping, orders, items_dict):
    """
    Print the orders assigned to the first pallet and the corresponding items
    in those orders, including their dimensions.

    Args:
        pallets:
            List of Pallet objects.
        order_pallet_mapping:
            Mapping from Order ID to Pallet ID.
        orders:
            Dictionary mapping Order ID to a list of Item IDs.
        items_dict:
            Dictionary mapping Item ID to Item objects.
    """
    if not pallets:
        print("No pallets available.")
        return

    first_pallet_id = pallets[0].id
    print(f"\n=== Detailed contents of pallet {first_pallet_id} ===")

    # Orders assigned to this pallet
    orders_on_first_pallet = [
        oid for oid, pid in order_pallet_mapping.items()
        if pid == first_pallet_id
    ]

    if not orders_on_first_pallet:
        print("No orders assigned to this pallet.")
        return

    orders_on_first_pallet = sorted(orders_on_first_pallet)
    print(f"Orders assigned to pallet {first_pallet_id}: {orders_on_first_pallet}\n")

    # Retrieve the pallet object
    first_pallet = next(p for p in pallets if p.id == first_pallet_id)

    # Print items order by order
    for order_id in orders_on_first_pallet:
        print(f"📦 Order {order_id}:")
        item_ids = orders[order_id]

        for iid in item_ids:
            base_item = items_dict[iid]

            # Find placed copies of this item on the pallet
            placed_items = [it for it in first_pallet.items if it.item_id == iid]

            if not placed_items:
                print(
                    f"  - Item {iid}: "
                    f"{base_item.length}x{base_item.width} (NOT ON PALLET!)"
                )
            else:
                for it in placed_items:
                    rot = "R" if it.rotated else "O"
                    print(
                        f"  - Item {iid} "
                        f"(excel: {base_item.length}x{base_item.width}) → "
                        f"pallet: {it.length}x{it.width}, "
                        f"rot={rot}, pos=({it.x},{it.y})"
                    )
        print("") 
