from .Component import Component
from .. import constants as const
import numpy as np


class Permeance(Component):
    def __init__(self, part_id=None, n1=None, n2=None, mur=3000, w=0, d=0, l=0, model_label=None):
        super().__init__(part_id, n1, n2)
        self.mur = mur
        self.mur_d = mur
        self.w = w
        self.d = d
        self.l = l
        self.model_label = model_label

    @property
    def value(self):
        return self.P()

    def P(self):
        value = (const.mu0 * self.mur * self.w * self.d) / self.l * 1e-3
        return value

    def dP(self):
        value = (const.mu0 * self.mur_d * self.w * self.d) / self.l * 1e-3
        return value

    def MMF(self, ports_v):
        n1 = self.n1 - 1
        n2 = self.n2 - 1
        u1 = 0
        u2 = 0

        if n1 >= 0: u1 = ports_v[n1]
        if n2 >= 0: u2 = ports_v[n2]
        return u1 - u2

    def PHI(self, ports_v):
        MMF = self.MMF(ports_v)
        phi = MMF * self.P()
        return phi

    def B(self, ports_v):
        MMF = self.MMF(ports_v)
        b = const.mu0 * self.mur * MMF / self.l * 1000
        return b

    def H(self, ports_v):
        MMF = self.MMF(ports_v)
        h = MMF / self.l * 1000
        return h
