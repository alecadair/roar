import numpy as np
import pandas as pd
from sympy import sympify, Number, SympifyError, sin, cos, tan, asin, acos, atan, sqrt, exp, log, ln, pi, E, deg, rad, Symbol
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
from sympy.utilities.lambdify import lambdify
from collections import defaultdict, deque
from decimal import Decimal
import re
import token
import tokenize
from io import StringIO

# Import debug_print function - handles case where this module is imported before roar_gui
try:
    from roar_gui import debug_print
except ImportError:
    try:
        from gui.roar_gui import debug_print
    except ImportError:
        # Fallback: define a no-op debug_print if roar_gui isn't available
        def debug_print(*args, **kwargs):
            pass

# Create degree-based trig functions by wrapping radian functions
# These convert degrees to radians before calling the trig function
def sind(angle_degrees):
    """Sine function that takes angle in degrees"""
    return sin(angle_degrees * pi / 180)

def cosd(angle_degrees):
    """Cosine function that takes angle in degrees"""
    return cos(angle_degrees * pi / 180)

def tand(angle_degrees):
    """Tangent function that takes angle in degrees"""
    return tan(angle_degrees * pi / 180)

def asind(value):
    """Arcsine function that returns angle in degrees"""
    return asin(value) * 180 / pi

def acosd(value):
    """Arccosine function that returns angle in degrees"""
    return acos(value) * 180 / pi

def atand(value):
    """Arctangent function that returns angle in degrees"""
    return atan(value) * 180 / pi


class ROAREquationSolver:
    def __init__(self, top_level_app, data_frames=None, device_corners=None):
        self.equations = {}
        self.variables = {}
        self.constants = {}
        # Delimiter pattern that preserves scientific notation (e.g., 1e-10, 100e-6)
        # This pattern splits on operators/whitespace but keeps numbers with scientific notation together
        self.delimiters = r"[\+\-\*/\^\(\)\s,;.]+|(?<![a-zA-Z])\d+(?:[eE][+-]?\d+)?"
        self.corners = []
        self.data_frames = []
        self.top_level_app = top_level_app
        self.device_corners = device_corners or {}  # Dict mapping device names to corner lists (None = global)
        self.lookup_vals = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                            'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgds', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                            'va', 'vds', 'vdsat', 'vgs', 'vth', 'pi')

        # Mathematical functions that should be available in equations
        self.math_functions = {
            'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
            'arcsin', 'arccos', 'arctan',  # Alternative names
            'sqrt', 'exp', 'log', 'ln', 'abs',
            'min', 'max', 'sum', 'mean', 'std'
        }

        if data_frames:
            for df in data_frames:
                self.data_frames.append(df)
    def clear_all_equations(self):
        self.equations = {}
        self.variables = {}
        self.constants = {}
        self.corners = []
        self.data_frames = []


    def add_equation(self, symbol, equation):
        if ":" in equation:
            self.equations[symbol] = equation
            return 0
        try:
            original_equation = equation

            # Handle scientific notation for constants
            if isinstance(equation, str) and 'e' in equation.lower():
                # Check if this is actually scientific notation (not just the letter 'e')
                # Match patterns like: 1e-10, 100e6, 2.5e+3
                sci_pattern = r'\d+\.?\d*[eE][+-]?\d+'
                matches = re.findall(sci_pattern, equation)
                for match in matches:
                    parts = match.lower().split('e')
                    if len(parts) == 2:
                        replacement = f"({parts[0]}*10**({parts[1]}))"
                        equation = equation.replace(match, replacement)

            # Extract all identifiers from the equation and pre-create Symbol objects
            # This avoids the "strict=True" error when sympify encounters undefined variables
            import token
            import tokenize
            from io import StringIO

            identifiers = set()
            try:
                tokens_list = tokenize.generate_tokens(StringIO(equation).readline)
                for tok in tokens_list:
                    if tok.type == token.NAME and tok.string not in ['and', 'or', 'not', 'in', 'is']:
                        identifiers.add(tok.string)
            except:
                # Fallback: use simple regex if tokenize fails
                identifiers = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', equation))

            # Create a local namespace with mathematical functions
            # NOTE: Trig functions now use DEGREES by default
            local_dict = {
                'sin': sind, 'cos': cosd, 'tan': tand,  # Degree-based trig functions
                'asin': asind, 'acos': acosd, 'atan': atand,  # Degree-based inverse trig
                'arcsin': asind, 'arccos': acosd, 'arctan': atand,  # aliases (degrees)
                'sind': sind, 'cosd': cosd, 'tand': tand,  # Explicit degree versions
                'asind': asind, 'acosd': acosd, 'atand': atand,  # Explicit degree inverse
                'sqrt': sqrt, 'exp': exp, 'log': log, 'ln': ln,
                'pi': pi, 'e': E, 'E': E
            }

            # Add all identifiers as Symbols to avoid "strict=True" errors
            for identifier in identifiers:
                if identifier not in local_dict:
                    local_dict[identifier] = Symbol(identifier)

            # Now sympify should work because all variables are pre-defined as Symbols
            sympified_equation = sympify(equation, locals=local_dict,
                                        rational=False, evaluate=True)

            self.equations[symbol] = sympified_equation

        except (SympifyError, TypeError, ValueError, NameError) as e:
            debug_print(f"Error adding equation '{symbol}': {e}")
            debug_print(f"  Equation string: '{equation}'")
            import traceback
            traceback.print_exc()
            # Do NOT store equation as string - this causes issues with dependency graph
            # Instead, store a simple constant or skip it
            self.equations[symbol] = sympify("0")  # Store as zero to avoid crashes

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

    def create_matrix_from_lookup(self, lookup, corner_dfs):
        column_vectors = []
        split_lookup = lookup.split(":")
        device = ""
        lookup_var = ""
        if len(split_lookup) > 1:
            device = split_lookup[1]
            lookup_var = split_lookup[0]
        else:
            lookup_var = split_lookup[0]

        # Determine which corners to use for this device
        device_specific_info = None
        device_specific_corners = None
        if device and device in self.device_corners:
            device_specific_info = self.device_corners[device]
            # Handle both old format (list) and new format (dict with 'corners' key)
            if isinstance(device_specific_info, dict):
                device_specific_corners = device_specific_info.get('corners')
            else:
                device_specific_corners = device_specific_info
            debug_print(f"[LOOKUP DEBUG] Device '{device}' has specific corners: {device_specific_corners}")

        # Filter corner_dfs if device has specific corners
        corners_to_use = corner_dfs
        if device_specific_corners is not None:
            # Device has custom corner selection
            if isinstance(corner_dfs, dict):
                # Filter to only the corners specified for this device
                # Handle both simple corner names and full path keys (PDK>model>length>corner)
                corners_to_use = {}
                for full_path, df in corner_dfs.items():
                    # Extract corner name from full path (last segment after '>')
                    corner_name = full_path.split('>')[-1] if '>' in full_path else full_path
                    if corner_name in device_specific_corners:
                        corners_to_use[full_path] = df
                debug_print(f"[LOOKUP DEBUG] Filtered corners for device '{device}': {list(corners_to_use.keys())}")
                if not corners_to_use:
                    debug_print(f"[LOOKUP DEBUG] WARNING: No matching corners found for device '{device}'!")
                    debug_print(f"[LOOKUP DEBUG]   Requested: {device_specific_corners}")
                    debug_print(f"[LOOKUP DEBUG]   Available corner names: {[k.split('>')[-1] if '>' in k else k for k in corner_dfs.keys()]}")
            elif isinstance(corner_dfs, list):
                # If corner_dfs is a list, we need corner names from somewhere else
                # For now, use all corners (global behavior)
                debug_print(f"[LOOKUP DEBUG] Device {device} has custom corners {device_specific_corners} but corner_dfs is a list")
                debug_print(f"[LOOKUP DEBUG] Cannot filter - using all {len(corner_dfs)} corners")
        else:
            # No device-specific corners, use all available corners (global selection)
            if device:
                debug_print(f"[LOOKUP DEBUG] Device '{device}' using global corner selection")
            else:
                debug_print(f"[LOOKUP DEBUG] No device specified, using global corner selection")

        #corner_collection = self.top_level_app.roar_design.devices[device].corner_collection
        #corners_to_eval = self.top_level_app.roar_design.
        for corner in corners_to_use if not isinstance(corners_to_use, dict) else corners_to_use.values():
        #for corner in corner_collection.corners:
            #df = corner.df
            df = corner
            #df = corner.df
            if lookup_var in df.columns:
                col_values = df[lookup_var].values
                column_vectors.append(col_values)
                # Debug: show what we extracted
                if len(column_vectors) == 1:  # Only print for first corner to avoid spam
                    unique_count = len(np.unique(col_values))
                    debug_print(f"[LOOKUP DEBUG] Extracting '{lookup_var}' from df: {len(col_values)} values, {unique_count} unique, range=[{np.min(col_values):.3f}, {np.max(col_values):.3f}]")
                    if device_specific_corners:
                        debug_print(f"[LOOKUP DEBUG]   Using device-specific corners for {device}: {device_specific_corners}")
                    if unique_count == 1:
                        debug_print(f"[LOOKUP DEBUG]   ⚠ WARNING: Column '{lookup_var}' has only ONE unique value in dataframe!")
                        debug_print(f"[LOOKUP DEBUG]   DataFrame shape: {df.shape}, columns: {list(df.columns[:5])}...")

        # Check if we found any data
        if not column_vectors:
            debug_print(f"[LOOKUP DEBUG] ⚠ WARNING: No data found for lookup '{lookup_var}' in any dataframe!")
            debug_print(f"[LOOKUP DEBUG]   Device: {device if device else 'None'}")
            debug_print(f"[LOOKUP DEBUG]   Available corners: {len(corners_to_use) if not isinstance(corners_to_use, dict) else len(corners_to_use)}")
            # Return empty array with proper shape instead of crashing
            if corner_dfs and len(corner_dfs) > 0:
                first_df = next(iter(corner_dfs.values())) if isinstance(corner_dfs, dict) else corner_dfs[0]
                nrows = first_df.shape[0] if hasattr(first_df, 'shape') else len(first_df)
                return np.zeros((nrows, 1)), corner_dfs
            else:
                return np.zeros((1, 1)), []

        # Stack the column vectors horizontally to form a 2D matrix
        matrix = np.column_stack(column_vectors)
        return matrix, corner_dfs if not isinstance(corners_to_use, dict) else list(corners_to_use.values())
        #return matrix

    def add_variable_from_dataframe(self, dataframe):
        for column in dataframe.columns:
            self.add_variable(column, dataframe[column].values)

    @staticmethod
    def is_number(s):
        pattern = r'^-?\d+(\.\d+)?$'
        s_str = str(s)
        # Check if the string matches the pattern
        is_number = bool(re.match(pattern, s_str))
        return is_number
        """
        try:
            float(s)
            return True
        except TypeError:
            return False
        """

    def evaluate_equations(self, symbols_to_add, corner_dfs=None):
        dependency_graph = self.build_dependency_graph()
        if self.has_cycle(dependency_graph):
            print("Error: The equations have cyclical dependencies.")
            return None
        # Topological sort
        sorted_equations = self.topological_sort(dependency_graph)
        symbols_to_add_strings = []
        for sym in symbols_to_add:
            symbols_to_add_strings.append(sym)
        if sorted_equations is None:
            return None
        sorted_equations.reverse()  # Process from the bottom up
        results = {}
        for equation in sorted_equations:
            # Check if this is a lookup by examining the equation value
            equation_value = self.equations.get(equation)
            is_lookup = (equation in self.lookup_vals or
                        (isinstance(equation_value, str) and ":" in equation_value))

            if is_lookup:
                # Special case for 3D meshgrid: check if the equation name itself exists as a column
                # For example, if equation="kgm1" and corner_dfs has a "kgm1" column, use it directly
                direct_column_found = False
                if corner_dfs and len(corner_dfs) > 0:
                    # Get first dataframe whether corner_dfs is a list or dict
                    first_df = next(iter(corner_dfs.values())) if isinstance(corner_dfs, dict) else corner_dfs[0]
                    if hasattr(first_df, 'columns') and equation in first_df.columns:
                        # Use the column directly!
                        debug_print(f"[LOOKUP DEBUG] Found '{equation}' as direct column in dataframe")
                        result = first_df[equation].values.reshape(-1, 1)
                        direct_column_found = True
                        results[equation] = result
                        unique_count = len(np.unique(result))
                        debug_print(f"[SOLVER DEBUG] Evaluated direct column '{equation}', shape: {result.shape}, unique={unique_count}, range=[{np.min(result):.3f}, {np.max(result):.3f}]")

                if not direct_column_found:
                    # For equation assignments like "kcgd4 = kcgd:M3", use the VALUE (kcgd:M3) for lookup
                    lookup_string = equation_value if isinstance(equation_value, str) else equation
                    result, corner_collection = self.create_matrix_from_lookup(lookup_string, corner_dfs=corner_dfs)
                    if equation in symbols_to_add_strings:
                        for corner in corner_collection:
                            print("TODO")
                    results[equation] = result
                    # Debug: show what the lookup returned
                    if hasattr(result, 'shape'):
                        unique_count = len(np.unique(result)) if isinstance(result, np.ndarray) else 'N/A'
                        debug_print(f"[SOLVER DEBUG] Evaluated lookup '{equation}', shape: {result.shape}, unique={unique_count}, range=[{np.min(result):.3f}, {np.max(result):.3f}]")
                    else:
                        debug_print(f"[SOLVER DEBUG] Evaluated lookup '{equation}', value: {result}")
                continue
            equation_to_evaluate = self.equations[equation]
            debug_print(f"[SOLVER DEBUG] Evaluating equation '{equation}' = {equation_to_evaluate}")
            debug_print(f"[SOLVER DEBUG]   Available in results: {list(results.keys())}")
            if self.is_number(equation_to_evaluate):
                # Store constant as scalar value
                # NumPy broadcasting will automatically expand it when used with arrays
                # This allows constants to work with device-specific lookups that have
                # different numbers of corners
                val = float(equation_to_evaluate)
                results[equation] = val
                continue
            result = self.evaluate_equation(equation_to_evaluate, results, corner_dfs=corner_dfs)
            if result is not None:
                corner_equation_dict = {}
                if equation in symbols_to_add_strings:
                    corner_count = 0
                    # Iterate over corner dataframes (handle both dict and list)
                    corner_dfs_iter = corner_dfs.values() if isinstance(corner_dfs, dict) else corner_dfs
                    for corner_df in corner_dfs_iter:
                        result_column = result[:, corner_count]
                        corner_df[equation] = result_column
                        corner_count += 1
                    #for device in self.top_level_app.roar_design.devices:
                    #    corner_count = 0
                    #    for corner in self.top_level_app.roar_design.devices[device].corner_collection.corners:
                    #        result_column = result[:, corner_count]
                    #        corner.df[equation] = result_column
                    #        corner_count += 1
                    #if equation not in self.top_level_app.lookups:
                    #    self.top_level_app.lookups = self.top_level_app.lookups + (equation,)
                results[equation] = result
            else:
                return None
        return results

    def evaluate_equation(self, symbolic_equation, results, corner_dfs=None):
        try:
            # Handle string equations (lookups like "kcgd:M3")
            if isinstance(symbolic_equation, str):
                # This shouldn't be evaluated here - it should have been handled as a lookup
                debug_print(f"Warning: evaluate_equation called with string: {symbolic_equation}")
                return None

            # Convert the symbolic equation to a lambda function
            free_syms = list(symbolic_equation.free_symbols)

            # Use numpy modules for better matrix/array support and include math functions
            numpy_modules = [
                'numpy',
                {
                    'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                    'arcsin': np.arcsin, 'arccos': np.arccos, 'arctan': np.arctan,
                    'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan,
                    'sqrt': np.sqrt, 'exp': np.exp, 'log': np.log, 'ln': np.log,
                    'abs': np.abs, 'min': np.minimum, 'max': np.maximum,
                    'pi': np.pi, 'e': np.e
                }
            ]

            func = lambdify(free_syms, symbolic_equation, modules=numpy_modules)

            # Build argument list for lambdify: prefer already-computed results; if a free symbol
            # corresponds to a lookup column (or contains ':'), create matrix(s) from corner_dfs.
            args = []
            for var in free_syms:
                name = str(var)
                if name in results:
                    args.append(results[name])
                    # Debug: show what we're getting from results
                    val = results[name]
                    if hasattr(val, 'shape'):
                        unique_count = len(np.unique(val)) if isinstance(val, np.ndarray) else 'N/A'
                        debug_print(f"[SOLVER DEBUG]     Using {name} from results: shape={val.shape}, unique={unique_count}, range=[{np.min(val):.3f}, {np.max(val):.3f}]")
                    else:
                        debug_print(f"[SOLVER DEBUG]     Using {name} from results: value={val}")
                elif (name in self.lookup_vals) or (":" in name):
                    # Pull lookup column arrays from corner_dfs
                    # USE THE PASSED corner_dfs if available, otherwise fall back to self.corners
                    try:
                        use_corners = corner_dfs if corner_dfs is not None else (self.corners if self.corners else [])
                        mat, _ = self.create_matrix_from_lookup(name, corner_dfs=use_corners)
                    except Exception:
                        # fall back to empty list
                        mat = None
                    args.append(mat)
                else:
                    # Unknown variable: pass the symbol itself so lambdify may error or treat as scalar
                    args.append(var)

            # Evaluate the lambda function with prepared args
            evaluated_equation = func(*args)

            # Ensure result is a numpy array for consistent handling
            if not isinstance(evaluated_equation, np.ndarray):
                if isinstance(evaluated_equation, (list, tuple)):
                    evaluated_equation = np.array(evaluated_equation)
                elif isinstance(evaluated_equation, (int, float)):
                    # Keep scalars as-is, they'll be broadcast as needed
                    pass

            return evaluated_equation
        except Exception as e:
            if symbolic_equation in results:
                result = results[symbolic_equation]
                return result
            debug_print(f"Error evaluating equation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def build_dependency_graph(self):
        dependency_graph = defaultdict(set)
        for name, equation in self.equations.items():
            # If equation is a string (lookup like "kgm:M1"), handle separately
            if isinstance(equation, str):
                # For lookup strings, just extract the variable part
                if ":" in equation:
                    var = equation.split(":")[0]
                    if var and var != name and var not in self.math_functions:
                        dependency_graph[name].add(var)
                continue

            # For SymPy expressions, use free_symbols to get actual symbols
            try:
                # Get all symbols from the SymPy expression
                free_syms = equation.free_symbols
                for sym in free_syms:
                    var = str(sym)
                    # Skip if it's the equation name itself or a math function
                    if var != name and var not in self.math_functions:
                        dependency_graph[name].add(var)
            except (AttributeError, TypeError):
                # Fallback: if equation doesn't have free_symbols, use string parsing
                variables = set(symbol for symbol in re.split(self.delimiters, str(equation)))
                for var in variables:
                    # Skip if it's:
                    # - the equation name itself
                    # - empty string
                    # - a plain number (integer or float)
                    # - scientific notation (e.g., 1e-10, 100e-6)
                    # - a mathematical function
                    if (var != name and var != "" and
                        not var.isdigit() and
                        not re.match(r'^-?\d+\.?\d*([eE][+-]?\d+)?$', var) and
                        var not in self.math_functions):
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
    """
    data = {
        'd': [1, 2, 3],
        'e': [4, 5, 6]
    }
    df = pd.DataFrame(data)
    
    solver = EquationSolver(top_level_app=None, data_frames=[df])
    """
    data = {
        'vgs': [0.5, 0.6, 0.7],
        'vds': [1.0, 1.2, 1.4],
        'ids': [0.001, 0.0015, 0.002]
    }
    df = pd.DataFrame(data)
    solver = ROAREquationSolver(top_level_app=None, data_frames=[df])
    # Add equations - order doesn't matter, solver figures out dependencies
    solver.add_equation('Gm', '2 * ids / vgs')  # transconductance
    solver.add_equation('Rds', 'vds / ids')  # output resistance
    solver.add_equation('gain', 'Gm * Rds')  # intrinsic gain
    solver.add_equation('power', 'vds * ids')  # DC power
    solver.add_equation('efficiency', 'gain / power')  # custom metric
    results = solver.evaluate_equations(symbols_to_add=['gain', 'efficiency'], corner_dfs=[df])
    # Print results
    if results is not None:
        for name, result in results.items():
            print(f'{name}: {result}')

    """        
    # Add equations
    solver.add_equation('a', 'b + c')
    solver.add_equation('b', '2 * d')
    solver.add_equation('c', 'g - 1')
    solver.add_equation('d', '4 - 1')
    solver.add_equation('e', 'g - 1')

    solver.add_equation('j', 'i * a')
    solver.add_equation('f', '3 * e')
    solver.add_equation('g', '2')
    solver.add_equation('h', 'd - 1')
    solver.add_equation('i', 'b*2/4')

    # Evaluate equations
    results = solver.evaluate_equations(symbols_to_add=['a', 'b', 'c', 'f', 'g', 'h', 'i'])
    if results is not None:
        for name, result in results.items():
            print(f'{name}: {result}')
    """
