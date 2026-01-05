# Warehouse Order Batching, Routing, and Picker Assignment Optimization

This repository contains the implementation developed as part of a **Master’s thesis at HEC Liège**.  
All intellectual property rights are reserved by the author.

The project focuses on solving an **integrated warehouse optimization problem** involving:
- Order batching (palletization with 2D constraints),
- Picker routing (Clarke–Wright savings heuristic),
- Picker-to-batch assignment (LPT-based),
- Simulated Annealing–based improvement procedures.

The objective is to minimize the **picking makespan** and improve routing efficiency in a wave-picking warehouse setting.

---

## 📁 Project Structure and Main Scripts

All Python files are named according to their **purpose** or the **main class/functionality** they contain.  
The logic and usage of each file are documented via **clear docstrings**.

Key scripts:

### 🔹 Greedy Initial Solution
- **`greedy_run.py`**  
  Runs the greedy initial solution (BBLF palletization + routing + picker assignment).

### 🔹 Visualization of First Instance
- **`visual_first_instance.py`**  
  Generates and saves pallet placement visualizations for the **100-order instance** during greedy palletization.

### 🔹 Fine-Tuning (Stage 1)
- **`fine_tuning.py`**  
  Performs the first round of parameter tuning for the Simulated Annealing algorithm.

### 🔹 Advanced Fine-Tuning (K-search)
- **`fine_tuning_more.py`**  
  Conducts extended fine-tuning using **fixed T₀ and α**, focusing on **K-search**.

### 🔹 Final Experiments
- **`run.py`**  
  Executes all experiments using the **selected parameters** and produces final experimental results.

---

## 📦 Core Components (Python Modules)

- **`palletization.py`**  
  BBLF-based palletization with EMS handling and feasibility checks.

- **`routing.py`**  
  Clarke–Wright routing and route distance computation.

- **`assignment.py`**  
  Greedy LPT-like picker assignment and makespan calculation.

- **`sa_improvement_routing.py`**  
  Simulated Annealing improvement procedures:
  - Routing-distance objective
  - Makespan objective  
  (Both returning the **best-found solution**.)

- **`pipeline.py`**  
  End-to-end greedy pipeline integrating palletization, routing, and assignment.

---

## 📊 Excel Files and Data (`resources/`)

All Excel files were **produced by the author** specifically for this research.

### 🔹 Warehouse Layout & Items
- **`10x90_warehouse_layout-item_list.xlsm`**  
  Item list with dimensions and warehouse layout information.

### 🔹 Order Lists
- **`100_order_list.xlsm`**
- **`200_order_list.xlsm`**
- **`300_order_list.xlsm`**
- **`500_order_list.xlsm`**
- **`1000_order_list.xlsm`**  
  Order instances with their corresponding item lists.

### 🔹 Experimental Results
- **`greedy_results.xlsx`**  
  Results of the greedy initial solution.

- **`grid_search_results.xlsx`**  
  Results of the first parameter tuning phase.

- **`grid_search_results_more.xlsx`**  
  Results of the extended fine-tuning experiments.

- **`FINAL_experiment_results_runtime.xlsx`**  
  Final experimental results including runtime statistics.

---

## 📌 Notes

- The codebase is intended for **research and academic use**.
- The implementation is tailored to **wave-picking warehouse systems**.
- All algorithms and experimental settings are documented in the corresponding thesis.

---

## 📜 License

This project is **not open-source**.  
Reuse, redistribution, or modification without explicit permission from the author is not allowed.
