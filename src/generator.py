
from cid import *


class ROARDevice:
    def __init__(self, model_name=None, instance_name=None):
        self.model_name = model_name
        self.instance_name = instance_name

    def serialize(self):
        # Convert ROARDevice attributes to a dictionary
        return {
            "model_name": self.model_name,
            "instance_name": self.instance_name
        }

    @classmethod
    def deserialize(cls, data):
        # Create a new ROARDevice object from the dictionary
        return cls(
            model_name=data.get("model_name"),
            instance_name=data.get("instance_name")
        )

class ROARTransistor(ROARDevice):
    def __init__(self, instance_name=None, model_name=None, ideal_width=0, ideal_length=0,
                 multiplier=1, kgm=1, id=1, corner_collection=None, lookup_corner=None, constraints=[]):
        super().__init__(model_name=model_name, instance_name=instance_name)
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

    def serialize(self):
        # Serialize the attributes of the base class (ROARDevice) and then add the attributes of ROARTransistor
        base_data = super().serialize()  # Get ROARDevice data
        transistor_data = {
            "ideal_width": self.ideal_width,
            "ideal_length": self.ideal_length,
            "phys_width": self.phys_width,
            "phys_length": self.phys_length,
            "num_fingers": self.num_fingers,
            "multiplier": self.multiplier,
            "kgm": self.kgm,
            "id": self.id
            #"corner_collection": self.corner_collection,  # Assuming corner_collection is serializable
            #"lookup_corner": self.lookup_corner,          # Assuming lookup_corner is serializable
            #"constraints": self.constraints               # Assuming constraints are serializable
        }
        base_data.update(transistor_data)  # Combine base and transistor-specific data
        return base_data

    @classmethod
    def deserialize(cls, data):
        # Deserialize the base class (ROARDevice) attributes first
        roar_device = super(ROARTransistor, cls).deserialize(data)

        # Deserialize the ROARTransistor specific attributes
        roar_device.ideal_width = data.get("ideal_width", 0)
        roar_device.ideal_length = data.get("ideal_length", 0)
        roar_device.phys_width = data.get("phys_width", 0)
        roar_device.phys_length = data.get("phys_length", 0)
        roar_device.num_fingers = data.get("num_fingers", 0)
        roar_device.multiplier = data.get("multiplier", 1)
        roar_device.kgm = data.get("kgm", 1)
        roar_device.id = data.get("id", 1)
        roar_lookups = {}
        #roar_device.corner_collection = data.get("corner_collection", None)
        #roar_device.lookup_corner = data.get("lookup_corner", None)
        #roar_device.constraints = data.get("constraints", [])

        return roar_device
class ROARPDKPrimitives:
    def __init__(self):
        self.min_fingers = 0
        self.min_width = 0
        self.min_length = 0


class ROARConstraint:
    def __init__(self):
        self.constraints = []


class ROARDesign:
    def __init__(self, devices=[]):
        self.devices = {}
        for device in devices:
            self.devices[device.instance_name] = device

    def set_corners_for_device(self, instance_name, corner_collection):
        if instance_name not in self.devices:
            self.add_device(ROARTransistor(instance_name=instance_name))
        self.devices[instance_name].corner_collection = corner_collection

    def add_device(self, roar_device):
        self.devices[roar_device.instance_name] = roar_device

    def serialize(self):
        # Serialize each device in the design
        return {
            "devices": {name: device.serialize() for name, device in self.devices.items()}
        }

    @classmethod
    def deserialize(cls, data):
        # Rebuild the ROARDesign from the saved data
        design = cls()
        for instance_name, device_data in data.get("devices", {}).items():
            design.add_device(ROARTransistor.deserialize(device_data))  # Assuming all devices are ROARDevices for simplicity
        return design
