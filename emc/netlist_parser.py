# -*- coding: iso-8859-1 -*-
# netlist_parser.py
# Netlist parser module
# Copyright 2006 Giuseppe Venturini

# This file is part of the ahkab simulator.
#
# Ahkab is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
#
# Ahkab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License v2
# along with ahkab.  If not, see <http://www.gnu.org/licenses/>.

"""Parse spice-like netlist files and generate circuits instances.

The syntax is explained in :doc:`help/Netlist-Syntax` and it's based on [#1]_
whenever possible.

.. [#1] http://newton.ex.ac.uk/teaching/CDHW/Electronics2/userguide/

Introduction
------------

This module has one main circuit that is expected to be useful to the end user:
:func:`parse_circuit`, which encapsulates parsing a netlist file and returns the
circuit, the simulation objects and the post-processing directives (such as
plotting instructions).

Additionally, the module provides utility functions related to parsing, among
which the end user may be interested in the :func:`convert` function, which allows
converting from SPICE-like representations of floats, booleans and strings to
their Python representations.

The last type of functions in the module are utility functions to go through the
netlist files and remove comments.

Except for the aforementioned functions, the rest seem to be more suitable for
developers than end users.

Overview
--------

Function for parsing
====================

.. autosummary::
    parse_circuit
    main_netlist_parser
    parse_elem_resistor
    parse_elem_vsource
    parse_elem_isource

Utility functions for conversions
=================================

.. autosummary::
    convert
    convert_units
    convert_boolean

Utility functions for file/txt handling
=======================================

.. autosummary::
    join_lines
    is_valid_value_param_string
    get_next_file_and_close_current


Module reference
----------------
"""

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

import sys
import os

from . import circuit
from . import components
from . import printing
from .py3compat import StringIO

def parse_circuit(filename, read_netlist_from_stdin=False):
    """Parse a SPICE-like netlist

    Directives are collected in lists and returned too, except for
    subcircuits, those are added to circuit.subckts_dict.

    **Returns:**

    (circuit_instance, analyses, plotting directives)
    """
    # Lots of differences with spice's syntax:
    # Support for alphanumeric node names, but the ref has to be 0. always
    # .end is not required, but if is used anything following it is ignored
    # many others, see doc.

    circ = circuit.Circuit(title="", filename=filename)

    if not read_netlist_from_stdin:
        ffile = open(filename, "r")
    else:
        buf = ""
        for aline in sys.stdin:
            buf += aline + "\n"
        ffile = StringIO(buf)

    file_list = [(ffile, "unknown", not read_netlist_from_stdin)]
    file_index = 0
    directives = []
    model_directives = []
    netlist_lines = []

    line_n = 0

    try:
        while ffile is not None:
            while True:
                line = ffile.readline()
                if len(line) == 0:
                    break  # check for EOF
                line_n = line_n + 1
                line = line.strip().lower()
                if line_n == 1:
                    # the first line is always the title
                    circ.title = line
                    continue
                elif len(line) == 0:
                    continue  # empty line is really empty after strip()
                line = join_lines(ffile, line)
                if line[0] == "*":  # comments start with *
                    continue

                # directives are grouped together and evaluated after
                # we have the whole circuit.
                # subcircuits are grouped too, but processed first
                if line[0] == ".":
                    line_elements = line.split()
                    if line_elements[0] == ".end":
                        break
                    elif line_elements[0] == ".model":
                        model_directives.append((line, line_n))
                    else:
                        directives.append((line, line_n))
                    continue

                else:
                    netlist_lines = netlist_lines + [(line, line_n)]

            file_index = file_index + 1
            ffile = get_next_file_and_close_current(file_list, file_index)
            # print file_list

    except NetlistParseError as npe:
        (msg,) = npe.args
        if len(msg):
            printing.print_general_error(msg)
        printing.print_parse_error(line_n, line)
        # if not read_netlist_from_stdin:
            # ffile.close()
        raise NetlistParseError(msg)

    models = parse_models(model_directives)
    circ += main_netlist_parser(circ, netlist_lines)
    circ.models = models
    return (circ, directives)


def main_netlist_parser(circ, netlist_lines):
    elements = []
    parse_function = {
        'i': lambda line: parse_elem_isource(line, circ),
        'r': lambda line: parse_elem_resistor(line, circ),
        'v': lambda line: parse_elem_vsource(line, circ),
    }
    try:
        for line, line_n in netlist_lines:
            # elements: detect the element type and call the
            # appropriate parsing function
            # we always use normal convention V opposite to I
            # n1 is +, n2 is -, current flows from + to -
            try:
                elements += parse_function[line[0]](line)
            except KeyError:
                raise NetlistParseError("Parser: do not know how to parse" +
                                        " '%s' elements." % line[0])
    #   Handle errors from individual parse functions
    except NetlistParseError as npe:
        (msg,) = npe.args
        if len(msg):
            printing.print_general_error(msg)
        printing.print_parse_error(line_n, line)
        raise NetlistParseError(msg)

    return elements


def get_next_file_and_close_current(file_list, file_index):
    if file_list[file_index - 1][2]:
        file_list[file_index - 1][0].close()
    if file_index == len(file_list):
        ffile = None
    else:
        ffile = open(file_list[file_index][1], "r")
        file_list[file_index][0] = ffile
    return ffile


def parse_models(models_lines):
    models = {}
    for line, line_n in models_lines:
        tokens = line.replace("(", "").replace(")", "").split()
        if len(tokens) < 3:
            raise NetlistParseError("parse_models(): syntax error in model" +
                                    " declaration on line " + str(line_n) +
                                    ".\n\t" + line)
        model_label = tokens[2]
        model_type = tokens[1]
        model_parameters = {}
        for index in range(3, len(tokens)):
            if tokens[index][0] == "*":
                break
            (label, value) = parse_param_value_from_string(tokens[index])
            model_parameters.update({label.upper(): value})
        if model_type == "ekv":
            model_iter = ekv.ekv_mos_model(**model_parameters)
            model_iter.name = model_label
        # elif model_type == "csw":
        #   model_parameters.update({'name':model_label})
        #   model_iter = switch.iswitch_model(**model_parameters)
        else:
            raise NetlistParseError("parse_models(): Unknown model (" +
                                    model_type + ") on line " + str(line_n) +
                                    ".\n\t" + line,)
        models.update({model_label: model_iter})
    return models


def parse_elem_resistor(line, circ):
    """Parses a resistor from the line supplied, adds its nodes to the circuit
    instance circ and returns a list holding the resistor element.

    **Parameters:**

    line : string
        The netlist line.
    circ : circuit instance
        The circuit instance to which the resistor is to be connected.

    **Returns:**

    elements_list : list
        A list containing a :class:`ahkab.components.Resistor` element.

    """
    line_elements = line.split()
    if len(line_elements) < 4 or (len(line_elements) > 4 and not line_elements[4][0] == "*"):
        raise NetlistParseError("parse_elem_resistor(): malformed line")

    ext_n1 = line_elements[1]
    ext_n2 = line_elements[2]
    n1 = circ.add_node(ext_n1)
    n2 = circ.add_node(ext_n2)

    value = convert_units(line_elements[3])

    if value == 0:
        raise NetlistParseError("parse_elem_resistor(): ZERO-valued resistors are not allowed.")

    elem = components.Resistor(part_id=line_elements[0], n1=n1, n2=n2, value=value)

    return [elem]

def parse_elem_vsource(line, circ):
    """Parses a voltage source from the line supplied, adds its nodes to the
    circuit instance and returns a list holding the element.

    **Parameters:**

    line : string
        The netlist line.
    circ : circuit instance
        The circuit in which the voltage source is to be inserted.

    **Returns:**

    elements_list : list
        A list containing a :class:`ahkab.components.sources.VSource` element.
    """
    line_elements = line.split()
    if len(line_elements) < 3:
        raise NetlistParseError("parse_elem_vsource(): malformed line")

    #elem = components.sources.VSource(part_id=line_elements[0], n1=n1, n2=n2,
    #                       dc_value=dc_value, ac_value=vac)
    elem = 1
    return [elem]


def parse_elem_isource(line, circ):
    """Parses a current source from the line supplied, adds its nodes to the
    circuit instance and returns a list holding the current source element.

    **Parameters:**

    line : string
        The netlist line.
    circ : circuit instance
        The circuit in which the current source is to be inserted.

    **Returns:**

    elements_list : list
        A list containing a :class:`ahkab.components.sources.ISource` element.
    """
    line_elements = line.split()
    if len(line_elements) < 3:
        raise NetlistParseError("parse_elem_isource(): malformed line")

    ext_n1 = line_elements[1]
    ext_n2 = line_elements[2]
    n1 = circ.add_node(ext_n1)
    n2 = circ.add_node(ext_n2)

    elem = components.sources.PHISource(part_id=line_elements[0], n1=n1, n2=n2,
                                        dc_value=dc_value, ac_value=iac)

    return [elem]

def convert_units(string_value):
    """Converts a value conforming to SPICE's syntax to ``float``.

    Quote from the SPICE3 manual:

        A number field may be an integer field (eg 12, -44), a floating point
        field (3.14159), either an integer or a floating point number followed
        by an integer exponent (1e-14, 2.65e3), or either an integer or a
        floating point number followed by one of the following scale factors:

        T = 1e12, G = 1e9, Meg = 1e6, K = 1e3, mil = 25.4x1e-6, m = 1e-3, u =
        1e-6, n = 1e-9, p = 1e-12, f = 1e-15

    :raises ValueError: if the supplied string can't be interpreted according
    to the above.

    **Returns:**

    num : float
        A float representation of ``string_value``.
    """

    if type(string_value) is float:
        return string_value  # not actually a string!
    if not len(string_value):
        raise NetlistParseError("")

    index = 0
    string_value = string_value.strip().upper()
    while(True):
        if len(string_value) == index:
            break
        if not (string_value[index].isdigit() or string_value[index] == "." or
                string_value[index] == "+" or string_value[index] == "-" or
                string_value[index] == "E"):
            break
        index = index + 1
    if index == 0:
        # print string_value
        raise ValueError("Unable to parse value: %s" % string_value)
        # return 0
    numeric_value = float(string_value[:index])
    multiplier = string_value[index:]
    if len(multiplier) == 0:
        pass # return numeric_value
    elif multiplier == "T":
        numeric_value = numeric_value * 1e12
    elif multiplier == "G":
        numeric_value = numeric_value * 1e9
    elif multiplier == "K":
        numeric_value = numeric_value * 1e3
    elif multiplier == "M":
        numeric_value = numeric_value * 1e-3
    elif multiplier == "U":
        numeric_value = numeric_value * 1e-6
    elif multiplier == "N":
        numeric_value = numeric_value * 1e-9
    elif multiplier == "P":
        numeric_value = numeric_value * 1e-12
    elif multiplier == "F":
        numeric_value = numeric_value * 1e-15
    elif multiplier == "MEG":
        numeric_value = numeric_value * 1e6
    elif multiplier == "MIL":
        numeric_value = numeric_value * 25.4e-6
    else:
        raise ValueError("Unknown multiplier %s" % multiplier)
    return numeric_value

def is_valid_value_param_string(astr):
    """Has the string a form like ``<param_name>=<value>``?

    .. note::

        No spaces.

    **Returns:**

    ans : a boolean
        The answer to the above question.
    """
    work_astr = astr.strip()
    if work_astr.count("=") == 1:
        ret_value = True
    else:
        ret_value = False
    return ret_value


def convert(astr, rtype, raise_exception=False):
    """Convert a string to a different representation

    **Parameters:**

    astr : str
        The string to be converted.
    rtype : type
        One among ``float``, if a ``float`` sould be parsed from ``astr``,
        ``bool``, for parsing a boolean or ``str`` to get back a string (no
        parsing).
    raise_exception : boolean, optional
        Set this flag to ``True`` if you wish for this function to raise
        ``ValueError`` if parsing fails.

    **Returns:**

    ret : object
        The parsed data.
    """
    if rtype == float:
        try:
            ret = convert_units(astr)
        except ValueError as msg:
            if raise_exception:
                raise ValueError(msg)
            else:
                ret = astr
    elif rtype == str:
        ret = astr
    elif rtype == bool:
        ret = convert_boolean(astr)
    elif raise_exception:
        raise ValueError("Unknown type %s" % rtype)
    else:
        ret = astr
    return ret


def parse_param_value_from_string(astr, rtype=float, raise_exception=False):
    """Search the string for a ``<param>=<value>`` couple and returns a list.

    **Parameters:**

    astr : str
        The string to be converted.
    rtype : type
        One among ``float``, if a ``float`` sould be parsed from ``astr``,
        ``bool``, for parsing a boolean or ``str`` to get back a string (no
        parsing).
    raise_exception : boolean, optional
        Set this flag to ``True`` if you wish for this function to raise
        ``ValueError`` if parsing fails.

    **Returns:**

    ret : object
        The parsed data. If the conversion fails and ``raise_exception`` is not
        set, a ``string`` is returned.

    * If ``rtype`` is ``float`` (the type), its default value, the method will
      attempt converting ``astr`` to a float. If the conversion fails, a string
      is returned.
    * If set ``rtype`` to ``str`` (again, the type), a string will always be
      returned, as if the conversion failed.

    This prevents ``'0'`` (str) being detected as ``float`` and converted to 0.0,
    ending up being a new node instead of the reference.

    Notice that in ``<param>=<value>`` there is no space before or after the equal sign.

    **Returns:**

    alist : ``[param, value]``
        where ``param`` is a string and ``value`` is parsed as described.
    """
    if not is_valid_value_param_string(astr):
        return (astr, "")
    p, v = astr.strip().split("=")
    v = convert(v, rtype, raise_exception=False)
    return p, v


class NetlistParseError(Exception):
    """Netlist parsing exception."""
    pass


def convert_boolean(value):
    """Converts the following strings to a boolean:
    yes, 1, true to True
    no, false, 0 to False

    raises NetlistParserException

    Returns: boolean
    """
    if value == 'no' or value == 'false' or value == '0' or value == 0:
        return_value = False
    elif value == 'yes' or value == 'true' or value == '1' or value == 1:
        return_value = True
    else:
        raise NetlistParseError("invalid boolean: " + value)

    return return_value


def join_lines(fp, line):
    """Read the lines coming up in the file. Each line that starts with '+' is added to the
    previous line (line continuation rule). When a line not starting with '+' is found, the
    file is rolled back and the line is returned.
    """
    while True:
        last_pos = fp.tell()
        next = fp.readline()
        next = next.strip().lower()
        if not next:
            break
        elif next[0] == '+':
            line += ' ' + next[1:]
        else:
            fp.seek(last_pos)
            break
    return line
