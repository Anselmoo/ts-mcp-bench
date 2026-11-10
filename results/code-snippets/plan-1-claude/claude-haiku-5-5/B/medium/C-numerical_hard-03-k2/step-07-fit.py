import numpy as np
from scipy.optimize import least_squares
m=np.load('mats.npz')
Hcf,H2,H4=m['Hcf'],m['H2'],m['H4']
ratio=None
def levels(Dq,B):
    # C/B=4.6 -> F4=0.7138 F2 ; B=(9F2-5F4)/441
    F4r=35*4.6/(9+5*4.6*0+0)  # placeholder
    # solve: C=35F4/441, B=(9F2-5F4)/441, C=4.6B
    # 35F4 = 4.6(9F2-5F4) -> 58 F4 = 41.4 F2
    F4=41.4/58; F2=1.0
    s=441*B/(9*F2-5*F4*F2)  # scale so B matches
    F2=F2*s; F4=F4*s
    H=Dq*Hcf+F2*H2+F4*H4
    e=np.linalg.eigvalsh(H)
    return e
def distinct(e,tol=1.0):
    out=[]
    for x in np.sort(e):
        if not out or x-out[-1][0]>tol: out.append([x,1])
        else: out[-1][1]+=1
    return out
# scan Dq at B=1 to see spectrum (in units) for ground identification
e=levels(2.0,1.0)
for v,deg in distinct(e)[:8]: print(round(v,3),deg)
