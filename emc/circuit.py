from . import non_linear_bh
from . import components


class Circuit(list):
    """The circuit class.

    **Parameters:**

    title : string
        The circuit title.

    filename : string, optional

        .. deprecated:: 0.09

        If the circuit instance corresponds to a netlist file on disk,
        set this to the netlist filename.

    """

    def __init__(self, title, filename=None):
        super(Circuit, self).__init__(self)
        self.title = title
        self.filename = filename
        self.nodes_dict = {}  # {int_node:ext_node, int_node:ext_node}
        self.internal_nodes = 0
        self.models = {}
        self.gnd = '0'

    def __str__(self):
        s = "* " + self.title + "\n"
        for elem in self:
            s += elem.get_netlist_elem_line(self.nodes_dict) + "\n"
        return s[:-1]

    def create_node(self, name):
        """Creates a new circuit node

        If there is a node in the circuit with the same name, ValueError is
        raised.

        **Parameters:**

        name : string
            the _unique_ identifier of the node.

        **Returns:**

        node : string
            the _unique_ identifier of the node, to be used for subsequent
            element declarations, for example.

        :raises ValueError: if a new node with the given id cannot be created,
          for example because a node with the same name already exists in the
          circuit. The only exception is the ground node, which has the
          reserved id ``'0'``, and for which this method won't raise any
          exception.
        :raises TypeError: if the parameter ``name`` is not of "text" type (what
          that means exactly depends on which version of Python you are using.)

        """
        if type(name) != str:
            raise TypeError("The node %s should have been of text type" %
                            name)

        got_ref = 0 in self.nodes_dict
        if name not in self.nodes_dict:
            if name == '0':
                int_node = 0
            else:
                int_node = int(len(self.nodes_dict) / 2) + 1 * (not got_ref)
            self.nodes_dict.update({int_node: name})
            self.nodes_dict.update({name: int_node})
        else:
            raise ValueError('Impossible to create new node %s: node exists!'
                             % name)
        return name

    def add_node(self, ext_name):
        """Adds the supplied node to the circuit, if needed.

        When a 'normal' (not the reference) node is added, a internal
        name (or label) is assigned to it.

        The nodes labels are stored in ``Circuit.nodes_dict``, as a dictionary of pairs
        like ``{int_node:ext_node}``.

        Those internal names are integers, by definition, and are generated
        starting from 1, then 2, 3, 4, 5...
        The integer ``0`` is reserved for the reference node (gnd), which is required
        for the circuit to be non-pathological and has ``ext_name=str(int_name)='0'``.

        Notice that this method doesn't halt or print errors if the node is already been
        added previously. It simply returns the internal node name assigned to it.

        **Parameters:**

        ext_name : string
            The unique identifier of the node.

        **Returns:**

        int_name : string
            the *unique* *internal* circuit identifier of the node.

        :raises TypeError: if the parameter ``ext_name`` is not of "text" type
          (what that means exactly depends on which version of Python you are
          using.)
        """
        # must be text (str unicode...)
        if type(ext_name) != str:
            raise TypeError("The node %s should have been of text type" %
                            ext_name)
        # test: do we already have it in the dictionary?
        if ext_name not in self.nodes_dict:
            if ext_name == '0':
                int_node = 0
            else:
                got_ref = 0 in self.nodes_dict
                int_node = int(len(self.nodes_dict) / 2) + 1 * (not got_ref)
            self.nodes_dict.update({int_node: ext_name})
            self.nodes_dict.update({ext_name: int_node})
        else:
            int_node = self.nodes_dict[ext_name]
        return int_node

    def get_nodes_number(self):
        """Returns the number of nodes in the circuit"""
        return int(len(self.nodes_dict) / 2)

    def ext_node_to_int(self, ext_node):
        """This function returns the integer id associated with an external node id.

        **Parameters:**

        ext_node : string
            The external node id to be converted.

        **Returns:**

        int_node : int
            The internal node associated.

        """
        return self.nodes_dict[ext_node]

    def int_node_to_ext(self, int_node):
        """This function returns the string id associated with the integer internal node id
        ``int_node``.

        **Parameters:**

        int_node : int
            The internal node id to be converted.

        **Returns:**

        ext_node : string
            the string id associated with ``int_node``.
        """
        return self.nodes_dict[int_node]

    def has_duplicate_elem(self):
        """Self-check for duplicate elements.

        No circuit should ever have duplicate elements
        (ie elements with the same ``part_id``).

        **Returns:**

        chk : boolean
            The result of the check.
        """
        all_ids = tuple(map(lambda e: e.part_id, self))
        return len(set(all_ids)) != len(all_ids)

    def get_ground_node(self):
        """Returns the reference node, AKA GND."""
        return '0'

    def get_elem_by_name(self, part_id):
        """Get a circuit element from its ``part_id`` value.

        If no matching element is found, the method returns
        ``None``. This may change in the future.

        **Parameters:**

        part_id : string
            The ``part_id`` of the element

        **Returns:**

        elem : circuit element
            Depending whether a matching element was found or not.

        :raises ValueError: if the element is not found.
        """
        for e in self:
            if e.part_id.lower() == part_id.lower():
                return e
        raise ValueError('Element %s not found' % part_id)

    def add_model(self, model_type, model_label, model_parameters):
        """Add a model to the available circuit models.

        **Parameters:**

        model_type : string
            the model type (eg "BH"). Right now, the possible values are:
            ``"BH"``

        model_label : string
            a unique identifier for the model being added (eg. ``"35PN210"``).

        model_parameters: dict
            a dictionary holding the parameters to be supplied to the
            model to instantiate it.

        """

        if 'name' not in model_parameters:
            model_parameters.update({'name': model_label})
        if model_type == "BH":
            model_iter = non_linear_bh.bh_model(**model_parameters)
            model_iter.name = model_label
        else:
            raise CircuitError("Unknown model type %s" % (model_type,))
        self.models.update({model_label: model_iter})

    def remove_model(self, model_label):
        """Remove a model from the available models.

        **Parameters:**

        model_label : string
            the unique identifier corresponding to the model
            being removed.

        .. note::

            This method currently silently ignores models that are not defined.

        """
        if self.models is not None and model_label in self.models:
            del self.models[model_label]
        # should print a warning here

    def add_permeance(self, part_id, n1, n2, mur, w, d, l, model_label):
        """Adds a permeance to the circuit.

        The permeance instance is added to the circuit elements
        and connected to the provided nodes. If the nodes are not
        found in the circuit, they are created and added as well.

        **Parameters:**

        part_id : string
            the reluctance part_id (eg "R1"). The first letter is replaced by an R

        n1, n2 : string
            the nodes to which the reluctance is connected.

        mur : float,
            The (initial) relative permeability

        w, d, l: float
            width, depth, length of the permeance P: (uA/l) ... A = w x d

        model_label : string
            the label of the model for non-linear characteristic
        """
        n1 = self.add_node(n1)
        n2 = self.add_node(n2)

        if w == 0 or d == 0 or l == 0:
            raise CircuitError("The parameter for the permeance are not allowed.")

        models = self.models
        if model_label is not None and model_label not in models:
            raise ModelError("Unknown BH model id: " + model_label)

        elem = components.Permeance(part_id=part_id, n1=n1, n2=n2, mur=mur, w=w, d=d, l=l, model_label=model_label)
        self.append(elem)

    def add_mmf_source(self, part_id, n1, n2, value):
        """Adds a mmf source to the circuit (also takes care that the nodes
        are added as well).

        **Parameters:**

        part_id : string
            The mmf source part_id (eg "VA"). The first letter is always V.
        n1, n2 : string
            The nodes to which the element is connected. Eg. ``"in"`` or
            ``"out_a"``.
        value : float
            mmf value
        """
        n1 = self.add_node(n1)
        n2 = self.add_node(n2)

        elem = components.sources.MMFSource(part_id=part_id, n1=n1, n2=n2, value=value)
        self.append(elem)

    def add_phi_source(self, part_id, n1, n2, value):
        """Adds a flux source to the circuit (also takes care that the nodes
        are added as well).

        **Parameters:**

        part_id : string
            The flux source ID (eg ``"IA"`` or ``"I3"``). The first letter
            is always I.
        n1, n2 : string
            The nodes to which the element is connected, eg. ``"in"`` or ``"out1"``.
        value : float
            flux value.
        """
        n1 = self.add_node(n1)
        n2 = self.add_node(n2)

        elem = components.sources.PHISource(part_id=part_id, n1=n1, n2=n2, value=value)
        self.append(elem)

    def get_MMFs_number(self):
        count = 0
        for elem in self:
            if isinstance(elem, components.sources.MMFSource):
                count += 1

        return count

class CircuitError(Exception):
    """General circuit assembly exception."""
    pass


class ModelError(Exception):
    """Model not found exception."""
    pass
