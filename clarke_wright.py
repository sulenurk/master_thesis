# clarke_wright.py

class ClarkeWrightSolver:
    def __init__(self, item_item_dist, depot_dist_df):
        self.item_item_dist = item_item_dist  # DataFrame
        # depot_dist_df: columns ['Item ID', 'Depot_Distance']
        self.depot_dist = depot_dist_df.set_index('Item ID')['Depot_Distance']

    def calculate_savings(self, items):
        """
        Compute Clarke–Wright savings while explicitly accounting for
        repeated occurrences of the same item.
        """
        savings = {}
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item_i = items[i]
                item_j = items[j]
                saving = (
                    self.depot_dist[item_i]
                    + self.depot_dist[item_j]
                    - self.item_item_dist.loc[item_i, item_j]
                )
                savings[(i, j)] = saving
        return savings

    def solve(self, items_to_route):
        """
        Generate a picking route using the Clarke–Wright savings heuristic
        while preserving duplicate items as separate visits.
        """
        if not items_to_route:
            return ['Depot', 'Depot']

        items = items_to_route.copy()

        # Assign temporary unique IDs to preserve duplicate items
        temp_ids = [f"{item}_{i}" for i, item in enumerate(items)]
        item_mapping = dict(zip(temp_ids, items))

        # Initialize each item as a separate route
        routes = [[tid] for tid in temp_ids]

        # Compute savings
        savings = self.calculate_savings(items)
        sorted_savings = sorted(savings.items(), key=lambda x: x[1], reverse=True)

        # Iteratively merge routes based on savings
        for (i, j), _ in sorted_savings:
            route_i = next((r for r in routes if temp_ids[i] in r), None)
            route_j = next((r for r in routes if temp_ids[j] in r), None)

            if not route_i or not route_j or route_i == route_j:
                continue

            if route_i[-1] == temp_ids[i] and route_j[0] == temp_ids[j]:
                new_route = route_i + route_j
            elif route_j[-1] == temp_ids[j] and route_i[0] == temp_ids[i]:
                new_route = route_j + route_i
            else:
                continue

            routes.remove(route_i)
            routes.remove(route_j)
            routes.append(new_route)

        # Build the final route with depot at start and end
        final_route = ['Depot']
        for route in routes:
            for tid in route:
                final_route.append(item_mapping[tid])
        final_route.append('Depot')

        return final_route
