import numpy as np
import pandas as pd
from sympy import sympify, Number, SympifyError
from sympy.utilities.lambdify import lambdify
from collections import defaultdict, deque
from decimal import Decimal
import re


class EquationSolver:
    def __init__(self, top_level_app, data_frames=None):
        self.equations = {}
        self.variables = {}
        self.constants = {}
        self.delimiters = r"[\+\-\*/\^\(\)\s,;.]+|\d+"
        self.corners = []
        self.data_frames = []
        self.top_level_app = top_level_app
        self.lookup_vals = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                            'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                            'va', 'vds', 'vdsat', 'vgs', 'vth', 'pi')
        self.corners = []
        if data_frames:
            for df in data_frames:
                self.data_frames.append(df)
                #self.add_variable_from_dataframe(df)

    def add_equation(self, name, equation):
        try:
            # Handle scientific notation for constants
            if isinstance(equation, str) and 'e' in equation:
                parts = equation.split('e')
                if len(parts) == 2 and parts[0].replace('.', '', 1).isdigit() and parts[1].replace('-', '', 1).isdigit():
                    equation = f"({parts[0]}*10**{parts[1]})"
            self.equations[name] = sympify(equation)
        except SympifyError as e:
            print(f"Error adding equation {name}: {e}")

    def remove_equation(self, name):
        if name in self.equations:
            del self.equations[name]

    def modify_equation(self, name, new_equation):
        if name in self.equations:
            self.equations[name] = sympify(new_equation)

    def add_variable(self, name, value):
        self.variables[name] = value

    def remove_variable(self, name):
        if name in self.variables:
            del self.variables[name]

    def create_matrix_from_lookup(self, var_name, corner=None):
        column_vectors = []
        for corner in self.corners:
            df = corner.df
            #df = corner.df
            if var_name in df.columns:
                column_vectors.append(df[var_name].values)
        # Stack the column vectors horizontally to form a 2D matrix
        matrix = np.column_stack(column_vectors)
        return matrix

    def add_variable_from_dataframe(self, dataframe):
        for column in dataframe.columns:
            self.add_variable(column, dataframe[column].values)

    @staticmethod
    def is_number(s):
        try:
            float(s)
            return True
        except TypeError:
            return False

    def evaluate_equations(self, symbols_to_add):
        dependency_graph = self.build_dependency_graph()
        if self.has_cycle(dependency_graph):
            print("Error: The equations have cyclical dependencies.")
            return None
        # Topological sort
        sorted_equations = self.topological_sort(dependency_graph)
        symbols_to_add_string = []
        for sym in symbols_to_add:
            symbols_to_add_string.append(sym.get())
        if sorted_equations is None:
            return None
        sorted_equations.reverse()  # Process from the bottom up
        results = {}
        for equation in sorted_equations:
            if equation in self.lookup_vals:
                result = self.create_matrix_from_lookup(equation)
                results[equation] = result
                continue
            equation_to_evaluate = self.equations[equation]
            if self.is_number(equation_to_evaluate):
                results[equation] = float(equation_to_evaluate)
                continue
            result = self.evaluate_equation(equation_to_evaluate, results)
            if result is not None:
                if equation in symbols_to_add_string:
                    corner_count = 0
                    for corner in self.corners:
                        result_column = result[:, corner_count]
                        corner.df[equation] = result_column
                    #if equation not in self.top_level_app.lookups:
                    #    self.top_level_app.lookups = self.top_level_app.lookups + (equation,)
                results[equation] = result
                print("add to data frames")
            else:
                return None
        return results

    def evaluate_equation(self, symbolic_equation, results):
        try:
            # Convert the symbolic equation to a lambda function
            func = lambdify(list(symbolic_equation.free_symbols), symbolic_equation, modules="numpy")

            # Evaluate the lambda function with results
            evaluated_equation = func(*[results.get(str(var), var) for var in symbolic_equation.free_symbols])

            return evaluated_equation
        except Exception as e:
            print("Error:", e)
            return None

    def build_dependency_graph(self):
        dependency_graph = defaultdict(set)
        for name, equation in self.equations.items():
            #variables = set(symbol for symbol in re.split(self.delimiters, str(equation)) if symbol.isalpha())
            variables = set(symbol for symbol in re.split(self.delimiters, str(equation)))

            for var in variables:
                if var != name and var != "":
                    dependency_graph[name].add(var)
        return dependency_graph

    def has_cycle(self, graph):
        visited = set()
        stack = set()

        def dfs(node):
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for neighbor in list(graph[node]):  # Make a copy of the neighbors to avoid modifying the graph
                if dfs(neighbor):
                    return True
            stack.remove(node)
            return False

        for node in list(graph):  # Make a copy of the nodes to avoid modifying the graph
            if dfs(node):
                return True
        return False

    def topological_sort(self, graph):
        indegree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                indegree[neighbor] += 1
        queue = deque(node for node in graph if indegree[node] == 0)
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in graph[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
        # Add nodes with no dependencies that are not in the graph
        for node in self.equations:
            if node not in result:
                result.append(node)
        return result

if __name__ == "__main__":
    # Example usage:
    data = {
        'd': [1, 2, 3],
        'e': [4, 5, 6]
    }
    df = pd.DataFrame(data)

    solver = EquationSolver(data_frames=[df])

    # Add equations
    solver.add_equation('a', 'b + c')
    solver.add_equation('b', '2 * d')
    solver.add_equation('c', 'g - 1')
    solver.add_equation('j', 'i * a')
    solver.add_equation('f', '3 * e')
    solver.add_equation('g', '2')
    solver.add_equation('h', 'd - 1')
    solver.add_equation('i', 'b*2/4')

    # Evaluate equations
    results = solver.evaluate_equations()
    if results is not None:
        for name, result in results.items():
            print(f'{name}: {result}')
