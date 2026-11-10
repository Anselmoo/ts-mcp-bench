python3 -c "
import ligand as M, numpy as np
from scipy.optimize import brentq
" 2>/dev/null; python3 -c "
import ligand as M, numpy as np
b=M.det_basis(6)
S2,Sz,Sp=M.S2_matrix(b)
w,v=np.linalg.eigh(S2); Q=v[:,np.abs(w)<1e-8]
B=1.0; C=4.5; F2=49*B+7*C; F4=63*C/5
# precompute parts linear in Dq: H = H0 + x*Hcf ; Hcf via difference
H0=M.hamiltonian(F2,F4,0.0,b)
H1=M.hamiltonian(F2,F4,1.0,b)-H0
H0s=Q.T@H0@Q; H1s=Q.T@H1@Q
def levels(x):
    ev=np.linalg.eigvalsh(H0s+x*H1s); return ev
def tri(x):
    ev=levels(x)-levels(x)[0]
    # find triplets: groups of 3 equal values
    out=[];i=1
    while i<len(ev)-2:
        if abs(ev[i]-ev[i+2])<1e-6 and abs(ev[i+1]-ev[i])<1e-6:
            out.append(ev[i]); i+=3
        else: i+=1
    return out
for x in [3.0,3.5,4.0]:
    print(x, np.round(tri(x)[:4],3))
ratio=23529/16611
def f(x):
    t=tri(x); return t[1]/t[0]-ratio
xs=brentq(f,3.0,4.0,xtol=1e-10)
t=tri(xs)
E1=t[0]; E2=t[1]
print('x=Dq/B',xs,'E1(B units)',E1,'E2',E2)
B_fit=16611/E1
print('B=',B_fit,'Dq=',xs*B_fit,'10Dq=',10*xs*B_fit,'C=',4.5*B_fit)
print('check E2*B', E2*B_fit)
"