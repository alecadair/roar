import numpy as np
import pandas as pd
from collections import defaultdict, deque

class EquationSolver:
    def __init__(self):
        self.equations = {}
        self.variables = {}
    
    def add_equation(self, name, equation):
        self.equations[name] = equation
    
    def remove_equation(self, name):
        if name in self.equations:
            del self.equations[name]
    
    def modify_equation(self, name, new_equation):
        if name in self.equations:
            self.equations[name] = new_equation
    
    def add_variable(self, name, value):
        self.variables[name] = value
    
    def remove_variable(self, name):
        if name in self.variables:
            del self.variables[name]
    
    def add_variable_from_dataframe(self, dataframe):
        for column in dataframe.columns:
            self.add_variable(column, dataframe[column].values)
    
    def evaluate_equations(self):
        dependency_graph = self.build_dependency_graph()
        if self.has_cycle(dependency_graph):
            print("Error: The equations have cyclical dependencies.")
            return None
        
        # Topological sort
        sorted_equations = self.topological_sort(dependency_graph)
        
        results = {}
        for equation in sorted_equations:
            result = self.evaluate_equation(self.equations[equation], results)
            if result is not None:
                results[equation] = result
            else:
                return None
        
        return results
    
    def evaluate_equation(self, symbolic_equation, results):
        try:
            symbolic_equation = ''.join(symbolic_equation.split())  # Remove white space characters
            variables_dict = {**self.variables, **results}
            result = eval(symbolic_equation, {}, variables_dict)
            return result
        except Exception as e:
            print("Error:", e)
            return None
    
    def build_dependency_graph(self):
        dependency_graph = defaultdict(set)
        for name, equation in self.equations.items():
            variables = set(symbol for symbol in equation.split() if symbol.isalpha())
            for var in variables:
                if var != name:
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
            
            # Remove node from the graph to prevent revisiting it
            del graph[node]
        
        # Check if there are any remaining nodes in the graph (cycles)
        if graph:
            print("Error: The equations have cyclical dependencies.")
            return None
        
        return result

# Example usage:
solver = EquationSolver()

# Add equations
solver.add_equation('a', 'b + c')
solver.add_equation('b', '2 * d')
solver.add_equation('c', 'd - 1')
solver.add_equation('d', '3 * e')
solver.add_equation('e', '2')

# Create a DataFrame
data = {
    'd': [1, 2, 3],
    'e': [4, 5, 6]
}
df = pd.DataFrame(data)

# Add variables from DataFrame
solver.add_variable_from_dataframe(df)

# Evaluate equations
results = solver.evaluate_equations()
if results is not None:
    for name, result in results.items():
        print(f'{name}: {result}')