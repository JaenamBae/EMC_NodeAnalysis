import numpy as np
from emc import components


def update_mur(circ, x):
    for elem in circ:
        if isinstance(elem, components.Permeance):
            if elem.model_label is not None:
                model = circ.models[elem.model_label]
                H = abs(elem.H(x))

                # update relative permeability
                elem.mur = model.mur(H)
                elem.mur_d = model.mur_d(H)


def make_system_matrix(circ, u_prev):
    update_mur(circ, u_prev)

    n_size = u_prev.shape[0]
    dA = np.zeros((n_size, n_size))
    A = np.zeros((n_size, n_size))
    b = np.zeros((n_size, 1))

    for elem in circ:
        n1 = elem.n1 - 1
        n2 = elem.n2 - 1
        if isinstance(elem, components.Permeance):
            if n1 >= 0:
                A[n1, n1] = A[n1, n1] + 1.0 * elem.P()
                dA[n1, n1] = dA[n1, n1] + 1.0 * elem.dP()
            if n2 >= 0:
                A[n2, n2] = A[n2, n2] + 1.0 * elem.P()
                dA[n2, n2] = dA[n2, n2] + 1.0 * elem.dP()
            if n1 >= 0 and n2 >= 0:
                A[n1, n2] = A[n1, n2] - 1.0 * elem.P()
                dA[n1, n2] = dA[n1, n2] - 1.0 * elem.dP()

                A[n2, n1] = A[n2, n1] - 1.0 * elem.P()
                dA[n2, n1] = dA[n2, n1] - 1.0 * elem.dP()

        elif isinstance(elem, components.sources.PHISource):
            if n1 >= 0:
                b[n1, 0] = b[n1, 0] + elem.PHI()

            if n2 >= 0:
                b[n2, 0] = b[n2, 0] - elem.PHI()

        elif isinstance(elem, components.sources.MMFSource):
            pass
            # we'll add its lines afterwards

        else:
            print("BUG - Unknown linear element.")

    # process MMF-sources
    # for each MMF-source, introduce a new variable: the current flowing through it.
    # then we introduce a KVL equation to be able to solve the circuit
    index = circ.get_nodes_number() - 1
    for elem in circ:
        n1 = elem.n1 - 1
        n2 = elem.n2 - 1
        if isinstance(elem, components.sources.MMFSource):
            # KCL
            if n1 >= 0:
                A[n1, index] = +1.0
                dA[n1, index] = +1.0
            if n2 >= 0:
                A[n2, index] = -1.0
                dA[n2, index] = -1.0

            # KVL
            if n1 >= 0:
                A[index, n1] = +1.0
                dA[index, n1] = +1.0
            if n2 >= 0:
                A[index, n2] = -1.0
                dA[index, n2] = -1.0

            b[index, 0] = 1.0 * elem.MMF()
            index = index + 1

    b = b - A.dot(u_prev)
    #print('A, dAx, b: ', A, A_p, b)
    return dA, b


def solve_circuit(circ, gamma):
    # step 1: initialize x
    n_nodes = circ.get_nodes_number()
    n_MMFs = circ.get_MMFs_number()
    n_matrix_size = n_nodes + n_MMFs - 1
    x = np.zeros((n_matrix_size, 1))

    # step 2: apply Newton-Raphson method
    norm = 0
    iter = 0
    while True:
        (A, b) = make_system_matrix(circ, x)
        dx = np.linalg.solve(A, b)

        if iter == 0:
            x = dx
        else:
            x = x + gamma * dx

        err = np.linalg.norm(dx)
        if iter == 0:
            norm = err

        err = err / norm
        norm = np.linalg.norm(x)
        print('Iteration {0}, error: {1}'.format(iter, err))

        # 오차율 0.05, 반복수 1000번 이내로 한정 --> 적당히 조절해야 함
        if err < 0.001 or iter > 2000:
        #if iter >= 2:
            break
        iter = iter + 1

    # step 3: return the solution
    return x