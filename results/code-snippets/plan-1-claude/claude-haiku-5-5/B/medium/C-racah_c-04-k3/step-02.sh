mkdir -p /w && cat > /w/d3.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from functools import reduce
# spin-orbitals: index = 2*(m+2)+s
ms=[-2,-1,0,1,2]
modes=[(m,s) for m in ms for s in (0,1)]
N=len(modes)
I2=np.eye(2); Z=np.diag([1,-1]); a=np.array([[0,1],[0,0]])  # annihilation on 2-level: |1>->|0>
def kron_list(l): return reduce(np.kron,l)
def ann(j):
    ops=[Z]*j+[a]+[I2]*(N-j-1)
    return kron_list(ops)
c=[ann(j) for j in range(N)]
cd=[x.conj().T for x in c]
# sector N=3 indices
dim=2**N
occ=np.array([bin(i).count('1') for i in range(dim)])
idx3=np.where(occ==3)[0]
def restrict(M): return M[np.ix_(idx3,idx3)]
C=[restrict(x) for x in c]; CD=[restrict(x) for x in cd]
# convention: state |1> is index 1 in 2-level, a maps |1>->|0>: a=[[0,1],[0,0]] maps basis vector e1->e0 ✓ (column 1 -> row0)
# Hmm: a[0,1]=1 means a|1>=|0>. occupied=|1>? we need a|occ>=|empty>; so occupied = e1 ok.
# Jordan-Wigner sign: Z on earlier modes; fine.
def gaunt_c(m1,k,q,m3):  # ∫ conj(Y_{2m1}) conj(Y_{kq}) Y_{2m3}
    return (-1)**(m1+q)*float(gaunt(2,k,2,-m1,-q,m3))
def gaunt_d(m2,k,q,m4):  # ∫ conj(Y_{2m2}) Y_{kq} Y_{2m4}
    return (-1)**m2*float(gaunt(2,k,2,-m2,q,m4))
def ak(k,m1,m2,m3,m4):
    if abs(m1-m3)>0 and False: pass
    s=0.0
    for q in range(-k,k+1):
        s+=gaunt_c(m1,k,q,m3)*gaunt_d(m2,k,q,m4)
    return 4*pi/(2*k+1)*s
# build two-electron operator in sector: H2 = 1/2 sum V[i,j,k,l] c+_i c+_j c_l c_k
# V_{ij,kl}=<m1 m2|V|m3 m4> with spin: s_i==s_k, s_j==s_l ; F-coefficients per k
def Vcoef(i,j,k,l):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=modes[i],modes[j],modes[k],modes[l]
    if s1!=s3 or s2!=s4: return np.zeros(3)
    return np.array([ak(kk,m1,m2,m3,m4) for kk in (0,2,4)])
def build_H(Dq,B,Cc):
    F4=441*Cc/35.0
    F2=49*B+7*Cc   # from B=(9F2-5F4)/441, C=35F4/441
    F=np.array([0,F2,F4])
    # one-electron: real cubic projectors in m basis
    h=np.zeros((N,N),complex)
    # eg: dz2 = |0>, dx2-y2 = (|2>+|-2>)/sqrt2 ; t2g: |1>,|-1> combos and xy
    import numpy as np2
    vecs_eg=[]
    v=np.zeros(5,complex); v[2]=1; vecs_eg.append(v)
    v=np.zeros(5,complex); v[4]=1/sqrt(2); v[0]=1/sqrt(2); vecs_eg.append(v)
    Peg=sum(np.outer(v,v.conj()) for v in vecs_eg)
    Pt=np.eye(5)-Peg
    P=Dq*(6*Peg-4*Pt)
    for m in range(5):
        for m2 in range(5):
            for s in (0,1):
                h[2*m+s,2*m2+s]=P[m,m2]
    H1=sum(h[i,j]*cd[i]@c[j] for i in range(N) for j in range(N) if abs(h[i,j])>1e-12)
    H1=restrict(H1)
    # two-electron
    H2=np.zeros((len(idx3),len(idx3)),complex)
    for i in range(N):
        for j in range(N):
            for k in range(N):
                for l in range(N):
                    Vc=Vcoef(i,j,k,l)
                    val=Vc@F
                    if abs(val)<1e-12: continue
                    H2+=0.5*val*(CD[i]@CD[j]@C[l]@C[k])
    return H1+H2
EOF
cd /w && python3 -c "
import d3,numpy as np
H=d3.build_H(0,1.0,0.0)  # Dq=0,B=1 -> F2=49
print(np.round(np.linalg.eigvalsh(H),3)[:5])
"