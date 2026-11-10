import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
# real-space via complex spherical harmonics basis m=-2..2, spin
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
def ck(k,m1,m2):
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
def Rk(k,B,C):
    F0=0;F2=49*B+7*C;F4=63*C/5*... if False else None
