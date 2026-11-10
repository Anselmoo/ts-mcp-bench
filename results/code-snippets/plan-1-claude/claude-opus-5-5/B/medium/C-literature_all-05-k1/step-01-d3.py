import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2; ms=range(-2,3)
# c^k(m1,m2)
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(2*l+1)*gaunt(l,k,l,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def Fk(B,Cr): # F0=0
    F2=(49*B+7*Cr); F4=63*Cr/5*... if False else None
