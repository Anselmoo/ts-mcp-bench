cat > d3.py << 'EOF'
import numpy as np
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from functools import reduce
ms=[-2,-1,0,1,2]
modes=[(m,s) for m in ms for s in (0,1)]
N=len(modes)
I2=np.eye(2); Z=np.diag([1,-1]); a=np.array([[0,1],[0,0]])
def kron_list(l): return reduce(np.kron,l)
def ann(j):
    return kron_list([Z]*j+[a]+[I2]*(N-j-1))
c=[ann(j) for j in range(N)]
cd=[x.conj().T for x in c]
dim=2**N
occ=np.array([bin(i).count('1') for i in range(dim)])
idx3=np.where(occ==3)[0]
def restrict(M): return M[np.ix_(idx3,idx3)]
C=[restrict(x) for x in c]; CD=[restrict(x) for x in cd]
def gaunt_c(m1,k,q,m3): return (-1)**(m1+q)*float(gaunt(2,k,2,-m1,-q,m3))
def gaunt_d(m2,k,q,m4): return (-1)**m2*float(gaunt(2,k,2,-m2,q,m4))
def ak(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        s+=gaunt_c(m1,k,q,m3)*gaunt_d(m2,k,q,m4)
    return 4*pi/(2*k+1)*s
def Vcoef(i,j,k,l):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=modes[i],modes[j],modes[k],modes[l]
    if s1!=s3 or s2!=s4: return np.zeros(3)
    return np.array([ak(kk,m1,m2,m3,m4) for kk in (0,2,4)])
VC={}
for i in range(N):
  for j in range(N):
    for k in range(N):
      for l in range(N):
        v=Vcoef(i,j,k,l)
        if np.any(np.abs(v)>1e-12): VC[(i,j,k,l)]=v
def build_H(Dq,B,Cc):
    F4=441*Cc/35.0
    F2=49*B+7*Cc
    F=np.array([0,F2,F4])
    Peg=np.zeros((5,5),complex)
    v=np.zeros(5,complex); v[2]=1; Peg+=np.outer(v,v.conj())
    v=np.zeros(5,complex); v[4]=1/sqrt(2); v[0]=1/sqrt(2); Peg+=np.outer(v,v.conj())
    Pt=np.eye(5)-Peg
    P=Dq*(6*Peg-4*Pt)
    H1=np.zeros((len(idx3),len(idx3)),complex)
    for m in range(5):
        for m2 in range(5):
            if abs(P[m,m2])<1e-12: continue
            for s in (0,1):
                H1+=P[m,m2]*CD[2*m+s]@C[2*m2+s]
    H2=np.zeros((len(idx3),len(idx3)),complex)
    for (i,j,k,l),Vc in VC.items():
        H2+=0.5*(Vc@F)*(CD[i]@CD[j]@C[l]@C[k])
    return H1+H2
def spin2():
    Sz=[0.5*(cd[2*m]@c[2*m]-cd[2*m+1]@c[2*m+1]) for m in range(5)]
    Szt=sum(Sz)
    Sp=sum(cd[2*m]@c[2*m+1] for m in range(5))
    Sm=sum(cd[2*m+1]@c[2*m] for m in range(5))
    S2=Szt@Szt+0.5*(Sp@Sm+Sm@Sp)
    return restrict(S2)
EOF
python3 -c "
import d3,numpy as np
H=d3.build_H(0,1.0,0.0)
print(np.allclose(H,H.conj().T))
ev=np.linalg.eigvalsh(H)
print(np.unique(np.round(ev,3),return_counts=True))
S2=d3.spin2().real
print(np.unique(np.round(np.linalg.eigvalsh(S2),3),return_counts=True))
"