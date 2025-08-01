# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


from emc import circuit
from emc import analysis


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    circ = circuit.Circuit(title="EMC")
    gnd = circ.get_ground_node()

    circ.add_model('BH', '35PN210', {'file_name': '35PN210.tab', 'Kh': 0, 'Ke': 0})
    circ.add_mmf_source('MMF1', n1='n1', n2=gnd, value=10000)
    circ.add_permeance('Rc', n1='n1', n2='n2', mur=3000, w=10, d=10, l=120, model_label='35PN210')
    circ.add_permeance('Rg', n1='n2', n2=gnd, mur=1, w=10, d=10, l=1, model_label=None)

    print(circ)

    rc = circ.get_elem_by_name("Rc")
    rg = circ.get_elem_by_name("Rg")

    u = analysis.solve_circuit(circ, 1.0)
    print('airgap flux density: {0}'.format(rg.B(u)))

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
