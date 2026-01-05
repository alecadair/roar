import json

class Database:
    def __init__(self, design_defaults, design_constraints):
        self.design_defaults = design_defaults
        self.design_constraints = design_constraints

    def load_design(self, name):
        with open(self.design_defaults, "r") as f:
            self.defaults = json.load(f)
        with open(self.design_constraints, "r") as f:
            self.constraints = json.load(f)

        return self.defaults, self.constraints

    def get_optimization_parameters(self):
        # optimization_parameters
        return self.constraints["optimization_parameters"]
