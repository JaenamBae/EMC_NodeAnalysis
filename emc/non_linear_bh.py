import os
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from . import constants as const
from scipy.interpolate import interp1d
import matplotlib.pylab as pl


def fp(inter_bhcurve, x):
    eps = 1e-3
    return (inter_bhcurve(x + eps) - inter_bhcurve(x)) / eps


class bh_model:
    def __init__(self, name=None, file_name=None, Kh=0, Ke=0):
        self.name = "model_nonlinear_bh" if name is None else name
        bh_data = list()

        file_path = Path() / os.getcwd() / file_name
        file_path.touch()

        try:
            f = open(file_path, 'r', encoding='utf-8')
        except:
            raise Exception("could not open the bh-curve file: '"+file_name+"'")
        else:
            for row in f:
                line = row.split('\t')
                HB = np.array([line[0], line[1]])
                HB = HB.astype(np.float64)
                bh_data.append(HB)
            f.close()
            # 수렴보장을 위해 기울기가 mu0 인 데이터 점을 50개 더 추가한다.
            H_max = HB[0]
            B_max = HB[1]

            for i in range(50):
                H_ex = H_max * (2 + i * 10000)
                B_ex = B_max + const.mu0 * (H_ex - H_max)
                bh_data.append([H_ex, B_ex])

            BHCurve = np.array(bh_data)
            B = BHCurve[:, 1]# B data [Tesla]
            H = BHCurve[:, 0]# H data [A/m]
            inter_HB_curve = CubicSpline(H, B, bc_type='natural', extrapolate=bool)
            #inter_HB_curve = interp1d(H, B, bounds_error=False, fill_value=(B[0], B[-1]))
            #pl.plot(H, B, marker='.')
            #pl.show()

            uH_data = list()
            for H, B in bh_data:
                if B == 0:
                    ur = 0
                else:
                    ur = B / H
                uH_data.append([H, ur])
            uH_data[0][1] = uH_data[1][1] * 1.05
            HuCurve = np.array(uH_data)
            H = HuCurve[:, 0]  # H data
            u = HuCurve[:, 1]  # u data
            inter_Hucurve = CubicSpline(H, u, bc_type='natural', extrapolate=bool)
            #inter_Hucurve = interp1d(H, u, bounds_error=False, fill_value=(u[0], u[-1]))
            #pl.plot(H, u, marker='.')
            #pl.show()

            self.hb = inter_HB_curve
            self.hu = inter_Hucurve

    def mur(self, H):
        if H > 0:
            return self.hb(H)/H / const.mu0
        else:
            return self.hb(1) / const.mu0

    def dmu_dH(self, H):
        return fp(self.hu, H)

    def mur_d(self, H):
        mur = self.mur(H)
        dmur_dH = self.dmu_dH(H) / const.mu0
        mur_d = mur + dmur_dH * H
        return mur_d
