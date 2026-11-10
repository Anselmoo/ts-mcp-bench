cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
from scipy.linalg import eigh
np.set_printoptions(precision=4, suppress=True)
ms=[-2,-1,0,1,2]
# Gaunt-based angular coefficients A_k[m1,m2,m3,m4] for <m1 m2|1/r12|m3 m4>
def G(a,b,k,q):  # int Y_a Y_b Y_kq (a,b,q integers) with l=2
    return float(gaunt(2,2,k,a,b,q).evalf()) if abs(a+b+q)==0 or True else 0
def Ak(k,m1,m2,m3,m4):
    if m1-m3 != -(m2-m4) and False: pass
    tot=0
    for q in range(-k,k+1):
        # int Y_m1^* Y_m3 Y_kq^* = (-1)^(m1+q) int Y_{2,-m1} Y_{2,m3} Y_{k,-q}
        if abs(-m1+m3-q)>0 : pass
        g1 = ((-1)**(m1+q))*float(gaunt(2,2,k,-m1,m3,-q).evalf()) if abs(-m1+m3-q)==0 and abs(-q)<=k else 0.0
        # int Y_m2^* Y_m4 Y_kq = (-1)^m2 int Y_{2,-m2} Y_{2,m4} Y_kq
        g2 = ((-1)**m2)*float(gaunt(2,2,k,-m2,m4,q).evalf()) if abs(-m2+m4+q)==0 else 0.0
        tot+=g1*g2
    return 4*np.pi/(2*k+1)*tot
# precompute
Vt={}
for k in (0,2,4):
    arr=np.zeros((5,5,5,5))
    for i,m1 in enumerate(ms):
        for j,m2 in enumerate(ms):
            for a,m3 in enumerate(ms):
                for b,m4 in enumerate(ms):
                    if m1+m2==m3+m4:
                        arr[i,j,a,b]=Ak(k,m1,m2,m3,m4)
    Vt[k]=arr
# Check k=0 coefficient: should be 1 for all (ms conserved) -> sanity
print("A0 sample", Vt[0][0,0,0,0], Vt[0][0,1,0,1])
# one-electron cubic orbitals in complex basis (index by m)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[ms.index(m)]=c
    return v
s2=np.sqrt(2)
orbs={
 'xy': vec({2:1/(1j*s2),-2:-1/(1j*s2)}),
 'yz': vec({1:1/(1j*s2),-1:1/(1j*s2)}),
 'xz': vec({1:1/s2,-1:-1/s2}),
 'x2y2': vec({2:1/s2,-2:1/s2}),
 'z2': vec({0:1.0}),
}
t2g=[orbs['xy'],orbs['yz'],orbs['xz']]; eg=[orbs['x2y2'],orbs['z2']]
def hcf(Dq):
    h=np.zeros((5,5),complex)
    for v in t2g: h+=-4*Dq*np.outer(v,v.conj())
    for v in eg: h+=6*Dq*np.outer(v,v.conj())
    return h
# Build all-alpha determinant space: 3 electrons in 5 orbitals (indices 0..4)
dets=list(itertools.combinations(range(5),3))
def coulomb_matrix(F):
    # two-electron matrix in the all-alpha determinant basis via Slater rules
    # <ij|V|kl> = sum_k F^k A_k with ordering conventions; antisymmetrized
    Vf=lambda i,j,k,l: sum(F[kk]*Vt[kk][i,j,k,l] for kk in (0,2,4))
    n=len(dets); M=np.zeros((n,n),complex)
    # one-body part
    return Vf
def build(Dq,F):
    Vf=coulomb_matrix(F)
    h=hcf(Dq)
    n=len(dets); H=np.zeros((n,n),complex)
    # rotate orbital index: use cubic basis by transforming Coulomb: work in complex basis then transform
    # Use full second quantization in complex m-basis, then project. Simpler: rotate basis to cubic.
    return H
# Simpler: second-quantized in complex basis, all-alpha, 5 spin-orbitals
def apply_ops(state, ops):
    # state: sorted tuple of occupied orbitals; ops list of ('c'|'a', idx) applied right to left
    st=list(state); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in st: return None,0
            p=st.index(i); sign*= (-1)**p; st.pop(p)
        else:
            if i in st: return None,0
            # insert
            p=sum(1 for x in st if x<i); sign*=(-1)**p; st.insert(p,i)
    return tuple(st),sign
def H_full(Dq,F):
    n=len(dets); idx={d:i for i,d in enumerate(dets)}
    # one-electron matrix in m basis
    h1=hcf(Dq)
    # two-electron integral in m basis: <ab|V|cd> = sum_k F^k Vt[k][a,b,c,d] (electrons 1,2)
    # H_ee = 1/2 sum <ab|V|cd> c_a^+ c_b^+ c_d c_c
    H=np.zeros((n,n),complex)
    for d in dets:
        j=idx[d]
        # one-body: sum h_ab c_a^+ c_b
        for a in range(5):
            for b in range(5):
                if abs(h1[a,b])<1e-14: continue
                for p in range(3):  # replace orbital d[p] by... general: use c_a^+ c_b
                    pass
        for a in range(5):
            for b in range(5):
                if abs(h1[a,b])<1e-14: continue
                st,sg=apply_ops(d,[('c',a),('a',b)])
                if st is None: continue
                H[idx[st],j]+=h1[a,b]*sg
        for a in range(5):
            for b in range(5):
                for c in range(5):
                    for e in range(5):
                        val=sum(F[k]*Vt[k][a,b,c,e] for k in (0,2,4))
                        if abs(val)<1e-14: continue
                        st,sg=apply_ops(d,[('c',a),('c',b),('a',e),('a',c)])
                        if st is None: continue
                        H[idx[st],j]+=0.5*val*sg
    return H
def levels(Dq,F):
    H=H_full(Dq,F)
    w=np.linalg.eigvalsh((H+H.conj().T)/2)
    return w
if __name__=="__main__":
    F={0:0.0,2:1.0,4:0.625}
    w=levels(0.0,F)
    print(np.round(w,4))
EOF
cd /tmp && python3 d3.py