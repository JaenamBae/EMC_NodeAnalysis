class Component(object):
    """Base Component class.

    This component is not meant for direct use, rather all other (simple)
    components are a subclass of this element.

    """

    def __init__(self, part_id=None, n1=None, n2=None):
        self.part_id = part_id
        self.n1 = n1
        self.n2 = n2

    #   Used by `get_netlist_elem_line` for value
    def __str__(self):
        return str(self.value)

    # It returns the flux flowing into the element
    def phi(self):
        return 0

    def get_netlist_elem_line(self, nodes_dict):
        return "%s %s %s %g" % (self.part_id, nodes_dict[self.n1],
                                nodes_dict[self.n2], self.value)
