mkdir -p /tmp/w && cat > /tmp/w/ligand.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt

ms=[-2,-1,0,1,2]
def tensors():
    Fk={2:1.0,4:1.0}   # coefficients of F2,F4 separately
    out={}
    for k in (2,4):
        Ck={}
        for q in range(-k,k+1):
            M=np.zeros((5,5))
            for ia,ma in enumerate(ms):
                for ic,mc in enumerate(ms):
                    if ma-mc!=q: continue
                    g=float(gaunt(2,k,2,-ma,q,mc))*(-1)**ma
                    M[ia,ic]=sqrt(4*pi/(2*k+1))*g
            Ck[q]=M
        V=np.zeros((5,5,5,5))
        for a,b,c,d in itertools.product(range(5),repeat=4):
            s=0.0
            for q in range(-k,k+1):
                s+=(-1)**q*Ck[q][a,c]*Ck[-q][b,d]
            V[a,b,c,d]=s
        out[k]=V
    return out

T=tensors()
def cf_one_body(Dq):
    h=np.zeros((5,5),dtype=complex)
    I=np.eye(5)
    v_eg=[I[2], (I[4]+I[0])/sqrt(2)]
    v_t2g=[(I[4]-I[0])/(1j*sqrt(2)), (I[3]-I[1])/sqrt(2), (I[3]+I[1])/(1j*sqrt(2))]
    for v in v_eg: h+=6*Dq*np.outer(v,v.conj())
    for v in v_t2g: h+=-4*Dq*np.outer(v,v.conj())
    return h

# spin orbitals: index = 2*orb + spin (spin 0 up,1 down)
def det_basis(nel=6, nso=10):
    return [sum(1<<i for i in c) for c in itertools.combinations(range(nso),nel)]

def apply_ops(state, ops):
    # ops list of (type,i) applied right to left: ops[-1] acts first; type 'c' creation, 'a' annihilation
    s=state; sign=1
    for typ,i in reversed(ops):
        if typ=='c':
            if (s>>i)&1: return None,0
            sign*=(-1)**bin(s & ((1<<i)-1)).count('1')
            s|=(1<<i)
        else:
            if not (s>>i)&1: return None,0
            sign*=(-1)**bin(s & ((1<<i)-1)).count('1')
            s&=~(1<<i)
    return s,sign

def hamiltonian(F2,F4,Dq,basis,h1):
    idx={s:i for i,s in enumerate(basis)}
    N=len(basis)
    H=np.zeros((N,N))
    # one-body: sum_{ij} h_ij c_i^dag c_j, h in spin-orbital basis
    h=np.zeros((10,10))
    for o1 in range(5):
        for o2 in range(5):
            for sp in range(2):
                h[2*o1+sp,2*o2+sp]=h1[o1,o2].real
    # two-body: 1/2 sum V_abcd c_a^dag c_b^dag c_d c_c, with V = F2*T2 + F4*T4
    Vfull=F2*T[2]+F4*T[4]
    for col,s in enumerate(basis):
        for i in range(10):
            for j in range(10):
                if abs(h[i,j])<1e-14: continue
                ns,sg=apply_ops(s,[('c',i),('a',j)])
                if ns is None: continue
                H[idx[ns],col]+=h[i,j]*sg
        for o1,o2,o3,o4 in itertools.product(range(5),repeat=4):
            v=Vfull[o1,o2,o3,o4]
            if abs(v)<1e-12: continue
            for s1 in range(2):
              for s2 in range(2):
                a=2*o1+s1; b=2*o2+s2; c=2*o3+s2; d=2*o4+s1
                # sum over spins: <ab|V|cd> requires spin(a)=spin(c), spin(b)=spin(d)
                pass
            # spin-resolved: a=(o1,s1), b=(o2,s2), c=(o3,s1), d=(o4,s2)
            for s1 in range(2):
              for s2 in range(2):
                a=2*o1+s1; b=2*o2+s2; c=2*o3+s1; d=2*o4+s2
                ns,sg=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
                if ns is None: continue
                H[idx[ns],col]+=0.5*v*sg
    return H

def S2_matrix(basis):
    # total S^2 = S_z^2 + (S+S- + S-S+)/2 ; compute via Sz and S+S-
    idx={s:i for i,s in enumerate(basis)}
    N=len(basis)
    Sz=np.zeros(N); S2=np.zeros((N,N))
    for col,s in enumerate(basis):
        nup=sum((s>>(2*o))&1 for o in range(5)); ndn=sum((s>>(2*o+1))&1 for o in range(5))
        Sz[col]=0.5*(nup-ndn)
        # S- S+ : S+ = sum_o c_up^dag c_dn
        # S+S- acting: sum over orbitals
        for o1 in range(5):
            for o2 in range(5):
                # S- = sum c_{o1,dn}^dag c_{o1,up} ; S+ = sum c_{o2,up}^dag c_{o2,dn}
                ns,sg=apply_ops(s,[('c',2*o2),('a',2*o2+1)])  # S+ with same orbital part
                # full S+ = sum_o (c_{o,up}^dag c_{o,dn}); do all terms
        pass
    # construct S+ and S- matrices
    Sp=np.zeros((N,N)); 
    for col,s in enumerate(basis):
        for o in range(5):
            ns,sg=apply_ops(s,[('c',2*o),('a',2*o+1)])
            if ns is not None: Sp[idx[ns],col]+=sg
    Sm=Sp.T
    S2=Sm@Sp + np.diag(Sz**2) + np.diag(Sz)  # S^2 = S-S+ + Sz^2 + Sz
    return S2, Sz
EOF
cd /tmp/w && timeout 600 python3 -c "
import ligand as L, numpy as np
print('built tensors')
"