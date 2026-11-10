python3 -c "
import ligand as M, numpy as np
from scipy.optimize import brentq
b=M.det_basis(6)
S2,Sz,Sp=M.S2_matrix(b)
w,v=np.linalg.eigh(S2); Q=v[:,np.abs(w)<1e-8]
B=1.0; C=4.5; F2=49*B+7*C; F4=63*C/5
H0=M.hamiltonian(F2,F4,0.0,b)
H1=M.hamiltonian(F2,F4,1.0,b)-H0
H0s=Q.T@H0@Q; H1s=Q.T@H1@Q
def levels(x): return np.linalg.eigvalsh(H0s+x*H1s)
def tri(x):
    ev=levels(x)-levels(x)[0]
    out=[];i=1
    while i<len(ev)-2:
        if abs(ev[i]-ev[i+2])<1e-6 and abs(ev[i+1]-ev[i])<1e-6:
            out.append(ev[i]); i+=3
        else: i+=1
    return out
ratio=23529/16611
f=lambda x: tri(x)[1]/tri(x)[0]-ratio
xs=brentq(f,3.0,4.0,xtol=1e-10)
t=tri(xs); E1,E2=t[0],t[1]
B_fit=16611/E1
print('x=Dq/B',xs,'E1',E1,'E2',E2)
print('B=',B_fit,'Dq=',xs*B_fit,'C=',4.5*B_fit,'E2 check',E2*B_fit)
"