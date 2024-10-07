
from cid import *


class ROARTransistor:
    def __init__(self, instance_name=None, model_name=None, ideal_width=0, ideal_length=0,
                 multiplier=1, kgm=1, id=1, corner_collection=None, lookup_corner=None, constraints=[]):
        self.instance_name = instance_name
        self.model_name = model_name
        self.ideal_width = ideal_width
        self.ideal_length = ideal_length
        self.phys_width = 0
        self.phys_length = 0
        self.num_fingers = 0
        self.multiplier = multiplier
        self.kgm = kgm
        self.id = id
        self.corner_collection = corner_collection
        self.lookup_corner = lookup_corner
        self.constraints = constraints

    def physical_sizes(self, roar_pdk_primitives):
        print("TODO")

class ROARPDKPrimitives:
    def __init__(self):
        self.min_fingers = 0
        self.min_width = 0
        self.min_length = 0

class ROARConstraint:
    def __init__(self):
        self.constraints = []


