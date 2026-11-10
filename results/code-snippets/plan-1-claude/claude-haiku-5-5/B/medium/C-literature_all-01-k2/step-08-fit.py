import numpy as np
from scipy.optimize import fsolve
import d8
# H is linear: H = B*HB + C*HC + Dq*HD
def mats():
    z=d8.Hmat
    # extract linear pieces by finite evaluation
    H00=z(0,0,0); HB=z(1,0,0)-H00; HC=z(0,1,0)-H00; HD=z(0,0,1)-H00
    return H00,HB,HC,HD
H00,HB,HC,HD=mats()
def spec(B,Dq):
    H=H00+B*(HB+4.5*HC)+Dq*HD
    return np.sort(np.linalg.eigvalsh(H).real)
def cl(ev,tol=1.0):
    out=[];
    for e in ev:
        if out and abs(e-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([e,1])
    return out
def bands(x):
    B,Dq=x
    ev=spec(B,Dq)
    c=cl(ev)
    g=c[0][0]
    return g, c
def resid(x):
    g,c=bands(x)
    # 3T2 = cluster 2 ; 3T1(2) = highest 3-fold cluster
    e_t2=c[1][0]
    e_t1p=[e for e,n in c if n==3][-1]
    return [ (e_t2-g)-4400, (e_t1p-g)-15500 ]
sol=fsolve(resid,[1000,440],xtol=1e-10)
print("B,Dq =",sol, "resid",resid(sol))
print([ (round(e,1),n) for e,n in bands(sol)[1]])
