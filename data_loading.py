# data_loading.py

import os
import re
from item import Item
import pandas as pd
import numpy as np


def load_data(items_file, orders_file):
    """
    Load item and order data from Excel files.

    Returns:
        items_dict:
            Dictionary mapping item IDs to Item objects.
        orders:
            Dictionary mapping order IDs to lists of item IDs.
        orders_df:
            Original orders DataFrame.
    """
    # Load items data
    items_df = pd.read_excel(items_file)
    items_dict = {
        row['Item ID']: Item(row['Item ID'], row['Length (cm)'], row['Width (cm)'])
        for _, row in items_df.iterrows()
    }

    # Load orders data
    orders_df = pd.read_excel(orders_file)
    orders = orders_df.groupby('Order ID')['Item ID'].apply(list).to_dict()

    return items_dict, orders, orders_df


def infer_aisle_length_from_filename(excel_file: str) -> float:
    """
    Infer the aisle length from the Excel filename.

    Example:
        '6x60_warehouse_layout-item_list.xlsm' -> 60 / 2 = 30

    The function searches for a '{number}x{number}' pattern in the filename
    and returns half of the second number as the aisle length.
    """
    basename = os.path.basename(excel_file)
    match = re.search(r'(\d+)[xX](\d+)', basename)
    if not match:
        raise ValueError(
            f"Cannot infer aisle_length from filename: {basename}. "
            f"Expected a pattern such as '6x60_...'"
        )

    second = int(match.group(2))
    return second / 2.0  # e.g., 60 -> 30.0


def create_distance_matrices(excel_file, sheet_name="Sheet1"):
    """
    Create item-to-item and depot-to-item distance matrices
    based on a warehouse layout stored in an Excel file.
    """
    # 0️⃣ Infer aisle length from the filename
    aisle_length = infer_aisle_length_from_filename(excel_file)

    # 1️⃣ Read data and validate columns
    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    required_columns = ['Item ID', 'Aisle', 'Position']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # 2️⃣ Convert data to NumPy arrays
    item_ids = df['Item ID'].values
    aisles = df['Aisle'].values
    x_coords = df['Aisle'].values
    y_coords = df['Position'].values

    # 3️⃣ Compute distance matrices
    aisle_i, aisle_j = np.meshgrid(aisles, aisles)
    x_i, x_j = np.meshgrid(x_coords, x_coords)
    y_i, y_j = np.meshgrid(y_coords, y_coords)

    # Distances for items in the same aisle
    same_aisle = np.abs(y_i - y_j)

    # Distances for items in different aisles
    cross_aisle = 5 * np.abs(x_i - x_j)
    front_entrance = y_i + y_j
    back_entrance = 2 * aisle_length - y_i - y_j + 2
    diff_aisle = np.minimum(front_entrance, back_entrance) + cross_aisle

    # Combined item-to-item distance matrix
    item_item_matrix = np.where(x_i == x_j, same_aisle, diff_aisle)

    item_item_df = pd.DataFrame(
        item_item_matrix,
        index=item_ids,
        columns=item_ids
    )

    # Depot-to-item distances
    depot_distances = 1.5 + 5 * (aisles - 1) + np.abs(y_coords - 1) + 0.5
    depot_distance_df = pd.DataFrame({
        'Item ID': item_ids,
        'Depot_Distance': depot_distances
    })

    return item_item_df, depot_distance_df
