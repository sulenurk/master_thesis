# picker_timeline.py

from typing import List, Optional
import pandas as pd
import matplotlib.pyplot as plt

def build_picker_schedule(
    picker_assignments: List[List[int]],
    pallet_distances: List[float],
    time_per_meter: float = 1.0
) -> pd.DataFrame:
    rows = []

    for picker_idx, pallet_ids in enumerate(picker_assignments, start=1):
        current_time = 0.0
        for pallet_id in pallet_ids:
            dist = pallet_distances[pallet_id - 1]
            duration = dist * time_per_meter
            rows.append({
                'picker': picker_idx,
                'pallet_id': pallet_id,
                'start': current_time,
                'end': current_time + duration,
                'distance': dist,
                'duration': duration
            })
            current_time += duration

    return pd.DataFrame(rows)


def plot_picker_gantt(
    schedule_df: pd.DataFrame,
    show: bool = True,
    filename: Optional[str] = None
):
    fig, ax = plt.subplots(figsize=(10, 6))

    pickers = sorted(schedule_df['picker'].unique())

    for i, picker in enumerate(pickers):
        picker_rows = schedule_df[schedule_df['picker'] == picker]
        for _, row in picker_rows.iterrows():
            start = row['start']
            end = row['end']
            width = end - start

            ax.barh(
                y=i,
                width=width,
                left=start,
                edgecolor='black',
                alpha=0.7
            )

            ax.text(
                x=start + width / 2,
                y=i,
                s=f"P{row['pallet_id']}",
                va='center',
                ha='center',
                fontsize=8
            )

    ax.set_yticks(range(len(pickers)))
    ax.set_yticklabels([f"Picker {p}" for p in pickers])
    ax.set_xlabel("Time")
    ax.set_ylabel("Picker")
    ax.set_title("Picker Timeline (Gantt Chart)")
    plt.tight_layout()

    if filename is not None:
        plt.savefig(filename)
    if show:
        plt.show()
    plt.close()
