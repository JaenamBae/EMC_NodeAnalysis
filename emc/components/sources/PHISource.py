from ..Component import Component
import numpy as np

class PHISource(Component):
    def __init__(self, part_id, n1, n2, value):
        super().__init__(part_id, n1, n2)
        self.value = value

    def __str__(self):
        rep = ""
        if self.value is not None:
            rep = rep + "type=phi value=" + str(self.value) + " "
        return rep

    def PHI(self):
        return self.value

    def get_netlist_elem_line(self, nodes_dict):
        rep = ""
        rep += "%s %s %s " % (self.part_id, nodes_dict[self.n1],
                             nodes_dict[self.n2])
        if self.value is not None:
            rep = rep + "type=phi value=" + str(self.value) + " "
        return rep

