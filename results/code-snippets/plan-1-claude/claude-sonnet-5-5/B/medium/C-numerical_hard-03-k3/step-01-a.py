import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <2m1|c^k|2m2> 
    q=m1-m2
    from sympy import sqrt
    return float((-1)**m1*sqrt(5)*sqrt(5)*gaunt(2,k,2,-m1,q,m2)*1) if abs(q)<=k else 0.0
# <m1|c^k|m2> = (-1)^m1 * 5 * 3j(2 -m1; k q; 2 m2)(2 0 k 0 2 0)... use gaunt form: c^k = sqrt(4pi/(2k+1)) int Y2m1* Ykq Y2m2
C={}
for k in (0,2,4):
  for a in ms:
    for b in ms:
      q=a-b
      C[k,a,b]=float((-1)**a*gaunt(2,k,2,-a,q,b)*np.sqrt(4*np.pi/(2*k+1))) if abs(q)<=k else 0.0
def V(F,a,b,c,d): # <ab|1/r12|cd>, a,c e1 ; b,d e2
  s=0
  for k,i in ((0,0),(2,1),(4,2)):
    # F^k/ (norm): F2=F^2/49,F4=F^4/441 convention
    s+=F[i]*C[k,a,c]*C[k,d,b]*(1 if a-c==d-b else 0) if False else 0
  return s
def Vm(F,a,b,c,d):
  if a+b!=c+d: return 0
  s=0
  for k,i in ((0,0),(2,1),(4,2)):
    s+=F[i]*C[k,c,a]*C[k,b,d]*0
  return s
