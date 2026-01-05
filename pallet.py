# pallet.py

import numpy as np
from ems import EMS
from item import Item
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.cm as cm
import os


class Pallet:
    def __init__(self, pallet_id, length=120, width=100):
        self.id = pallet_id
        self.length = length
        self.width = width
        self.items = []
        self.ems_list = [EMS(0, 0, length, width)]
        self.occupied_area = 0
        self.free_area = length * width

    def find_best_position(self, item):
        """
        Find the best placement position across all EMS regions (both unrotated and rotated).

        Scoring:
            Distance to the far (top-right) corner (favoring placements towards the far corner).
        """
        best_candidate = None
        best_score = -1
        far_corner = (self.length, self.width)

        for rotated in [False, True]:
            item_w = item.width if rotated else item.length
            item_h = item.length if rotated else item.width

            for ems in self.ems_list:
                if item_w <= ems.length and item_h <= ems.width:
                    # Place at the bottom-left corner of the EMS
                    px, py = ems.x, ems.y
                    dist = np.hypot(
                        far_corner[0] - (px + item_w),
                        far_corner[1] - (py + item_h)
                    )

                    if dist > best_score:
                        best_score = dist
                        best_candidate = {
                            "x": px,
                            "y": py,
                            "width": item_w,
                            "height": item_h,
                            "rotated": rotated,
                            "ems": ems
                        }
        return best_candidate

    def check_overlap(self, item):
        """Check whether the new item overlaps with any already placed item."""
        for existing in self.items:
            if not (
                item.x + item.length <= existing.x or
                existing.x + existing.length <= item.x or
                item.y + item.width <= existing.y or
                existing.y + existing.width <= item.y
            ):
                return True
        return False

    def clip_ems_by_item(self, ems, item):
        """
        Update (clip) an EMS region with respect to a newly placed item.

        Behavior:
            - If the item fully covers the EMS, the EMS is removed.
            - If there is no overlap, the EMS is kept unchanged.
            - If the item intrudes from the left/bottom edge, update boundaries accordingly.
            - If the item is placed inside the EMS, split into L-shaped regions.
            - Discard EMS regions smaller than 10x10.
        """
        ex, ey, ew, eh = ems.x, ems.y, ems.length, ems.width
        ix, iy, iw, ih = item.x, item.y, item.length, item.width
        new_ems = []

        # 1) If the item fully covers the EMS, remove it
        if (ix <= ex) and (iy <= ey) and (ix + iw >= ex + ew) and (iy + ih >= ey + eh):
            return []

        # 2) If there is no overlap, keep the EMS as is
        if (ix + iw <= ex) or (ix >= ex + ew) or (iy + ih <= ey) or (iy >= ey + eh):
            return [ems]

        # 3) Intrusion from the left side
        if ix <= ex < ix + iw:
            new_width = (ex + ew) - (ix + iw)
            if new_width >= 10:  # Minimum 10x10 rule
                new_ems.append(EMS(ix + iw, ey, new_width, eh))

        # 4) Intrusion from the bottom side
        if iy <= ey < iy + ih:
            new_height = (ey + eh) - (iy + ih)
            if new_height >= 10:  # Minimum 10x10 rule
                new_ems.append(EMS(ex, iy + ih, ew, new_height))

        # 5) Interior placement (L-shape splitting)
        if (ex < ix) and (ey < iy):
            # Right EMS (vertical)
            right_width = (ex + ew) - ix
            if right_width >= 10:
                new_ems.append(EMS(ix, ey, right_width, eh))

            # Top EMS (horizontal)
            top_height = (ey + eh) - iy
            if top_height >= 10:
                new_ems.append(EMS(ex, iy, ew, top_height))

        return new_ems if new_ems else []

    def update_ems_after_placement(self, item):
        """Update all EMS regions based on the newly placed item."""
        new_ems_list = []
        for ems in self.ems_list:
            # Check whether the EMS overlaps with the item
            if self._ems_overlaps_item(ems, item):
                clipped = self.clip_ems_by_item(ems, item)
                new_ems_list.extend(clipped)
            else:
                new_ems_list.append(ems)

        # Dominance pruning and removal of small EMS regions
        self.ems_list = self.prune_ems_list(new_ems_list)

    def _ems_overlaps_item(self, ems, item):
        """Check whether an item overlaps with an EMS region."""
        return not (
            item.x + item.length <= ems.x or
            ems.x + ems.length <= item.x or
            item.y + item.width <= ems.y or
            ems.y + ems.width <= item.y
        )

    def place_item(self, item):
        """Place an item at the best available position (if feasible)."""
        candidate = self.find_best_position(item)
        if not candidate:
            return False

        # Apply rotation if needed
        if candidate["rotated"]:
            item.rotate()

        item.x, item.y = candidate["x"], candidate["y"]

        # Overlap check
        if self.check_overlap(item):
            return False

        # Place the item and update pallet statistics
        self.items.append(item)
        self.occupied_area += item.length * item.width
        self.free_area -= item.length * item.width

        # Update ALL EMS regions
        new_ems_list = []
        for ems in self.ems_list:
            new_ems_list.extend(self.clip_ems_by_item(ems, item))

        self.ems_list = self.prune_ems_list(new_ems_list)
        return True

    def prune_ems_list(self, ems_list):
        """
        Apply dominance pruning and remove small EMS regions (edge < 10).
        """
        pruned = []
        for ems in ems_list:
            # 1) Skip if any edge length is smaller than 10
            if ems.length < 10 or ems.width < 10:
                continue

            # 2) Skip if this EMS is fully contained within another EMS
            keep = True
            for other_ems in ems_list:
                if ems == other_ems:
                    continue
                if (
                    ems.x >= other_ems.x and
                    ems.y >= other_ems.y and
                    ems.x + ems.length <= other_ems.x + other_ems.length and
                    ems.y + ems.width <= other_ems.y + other_ems.width
                ):
                    keep = False
                    break

            if keep:
                pruned.append(ems)
        return pruned

    def try_place_item(self, item):
        """Try placing an item, optionally rotating it if needed."""
        if self.place_item(item):
            return True
        item.rotate()
        if self.place_item(item):
            return True
        item.rotate()  # Restore original orientation
        return False

    def print_pallet_status(self):
        """Print the current pallet status."""
        print(f"\n📦 Pallet {self.id} (Dimensions: {self.length}x{self.width})")
        print(f"📌 Number of items placed: {len(self.items)}")
        print(f"📊 Occupied area: {self.occupied_area / (self.length * self.width) * 100:.2f}%")
        print("📐 EMS list:")
        for ems in self.ems_list:
            print(f"  - EMS: ({ems.x}, {ems.y}) → {ems.length}x{ems.width}")

    def visualize(self, filename="pallet_visualization.png", show_ems=True):
        """
        Visualize the current pallet layout.

        Args:
            filename:
                Output filename. If None, the plot is shown interactively.
            show_ems:
                Whether to display EMS regions.
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.set_xlim(0, self.length)
        ax.set_ylim(0, self.width)
        ax.set_aspect("equal")
        ax.set_title(
            f"Pallet {self.id} - Occupied: {self.occupied_area / (self.length * self.width) * 100:.1f}%"
        )

        # Pallet boundary
        ax.add_patch(Rectangle(
            (0, 0), self.length, self.width,
            fill=None, edgecolor="black", linewidth=2
        ))

        # Placed items
        # Map Order ID -> color
        order_ids = sorted(set(item.order_id for item in self.items))
        order_color_map = {
            oid: cm.tab20(i % 20)
            for i, oid in enumerate(order_ids)
        }

        for item in self.items:
            color = order_color_map[item.order_id]

            ax.add_patch(Rectangle(
                (item.x, item.y),
                item.length,
                item.width,
                facecolor=color,
                alpha=0.7,
                edgecolor="black"
            ))

            ax.text(
                item.x + item.length / 2,
                item.y + item.width / 2,
                f"O{item.order_id}\n{item.length}x{item.width}",
                ha="center",
                va="center",
                fontsize=7
            )

        # EMS regions
        if show_ems and self.ems_list:
            ems_colors = cm.get_cmap("tab20", len(self.ems_list))
            for idx, ems in enumerate(self.ems_list):
                color = ems_colors(idx)
                ax.add_patch(Rectangle(
                    (ems.x, ems.y),
                    ems.length,
                    ems.width,
                    facecolor=color,
                    alpha=0.2,
                    edgecolor="black",
                    linestyle="--"
                ))
                ax.text(
                    ems.x + ems.length / 2,
                    ems.y + ems.width / 2,
                    f"EMS\n{ems.length}x{ems.width}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="dimgrey"
                )

        plt.tight_layout()
        if filename:
            try:
                # Create the directory if it does not exist
                os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
                plt.savefig(filename)
                print(f"Visualization saved to: {filename}")
            except Exception as e:
                print(f"Failed to save visualization: {str(e)}")
        else:
            plt.show()
        plt.close()
