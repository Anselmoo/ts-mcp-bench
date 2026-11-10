import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
from scipy.optimize import fsolve

l=2
# complex orbitals m=-2..2 ; spin orbital index i = 2*mi + s
ms=list(range(-2,3))
def ang(k,m,q,mp):
    # <l m | C^k_q | l m'>
    g=float(N(gaunt(l,k,l,-m,q,mp)))
    return np.sqrt(4*np.pi/(2*k+1))*((-1)**(m%2))*g   # (-1)^m handled via parity below
# sign: (-1)^m for m integer
def ang2(k,m,q,mp):
    g=float(N(gaunt(l,k,l,-m,q,mp)))
    return np.sqrt(4*np.pi/(2*k+1))*((-1)**(abs(m)%2) if False else (-1)**m)*g
Ck={}
for k in (2,4):
    M=np.zeros((5,5,2*k+1))
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            for qi,q in enumerate(range(-k,k+1)):
                if abs(q)<=k and -m+q+mp==0:
                    M[i,j,qi]=ang2(k,m,q,mp)
    Ck[k]=M
# check: C^2 ~ Racah normalization <d||C2||d>; skip

def Vme(F2,F4):
    # build two-electron integrals <ab|V|cd> over spin orbitals
    F={2:F2,4:F4}
    V=np.zeros((10,10,10,10))
    for mi in range(5):
     for mj in range(5):
      for mk in range(5):
       for ml in range(5):
        for si in range(2):
         for sj in range(2):
          for sk in range(2):
           for sl in range(2):
            if si!=sk or sj!=sl: continue
            val=0.0
            for k in (2,4):
                M=Ck[k]
                for qi,q in enumerate(range(-k,k+1)):
                    # (-1)^q <a|C^k_q|c> <b|C^k_-q|d>
                    qm=-q; qmi=qm+k
                    val+=F[k]*((-1)**q)*M[mi,mk,qi]*M[mj,ml,qmi]
            V[2*mi+si,2*mj+sj,2*mk+sk,2*ml+sl]=val
    return V

def apply_ops(state, ops):
    # ops: list of (type,j) applied right-to-left ; type 'c' creation,'a' annihilation
    sgn=1; s=state
    for typ,j in reversed(ops):
        if typ=='a':
            if not (s>>j)&1: return None,0
            sgn*= (-1)**bin(s&((1<<j)-1)).count('1')
            s^=(1<<j)
        else:
            if (s>>j)&1: return None,0
            sgn*= (-1)**bin(s&((1<<j)-1)).count('1')
            s|=(1<<j)
    return s,sgn

# basis
states=[sum(1<<i for i in c) for c in itertools.combinations(range(10),6)]
idx={s:n for n,s in enumerate(states)}
D=len(states)

def build_op_1body(h):
    M=np.zeros((D,D))
    for n,s in enumerate(states):
        for a in range(10):
            for b in range(10):
                if abs(h[a,b])<1e-14: continue
                t,sg=apply_ops(s,[('c',a),('a',b)])
                if t is None: continue
                M[idx[t],n]+=sg*h[a,b]
    return M

def build_op_2body(V):
    M=np.zeros((D,D))
    nz=[(a,b,c,d,V[a,b,c,d]) for a in range(10) for b in range(10) for c in range(10) for d in range(10) if abs(V[a,b,c,d])>1e-12]
    for n,s in enumerate(states):
        for a,b,c,d,v in nz:
            t,sg=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
            if t is None: continue
            M[idx[t],n]+=0.5*sg*v
    return M

# cubic field projectors in complex basis (m index)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=np.sqrt(2)
orbs_t2g=[vec({-1:1/r2,1:-1/r2}), vec({-1:1j/r2,1:1j/r2}), vec({-2:1j/r2,2:-1j/r2})]
orbs_eg=[vec({0:1}), vec({-2:1/r2,2:1/r2})]
P_t2g=sum(np.outer(v,v.conj()) for v in orbs_t2g)
P_eg=sum(np.outer(v,v.conj()) for v in orbs_eg)
def spinexpand(P):
    h=np.zeros((10,10),complex)
    for mi in range(5):
        for mj in range(5):
            for s in range(2):
                h[2*mi+s,2*mj+s]=P[mi,mj]
    return h

# S^2
Sp=np.zeros((10,10)); Sz=np.zeros((10,10))
for mi in range(5):
    Sz[2*mi,2*mi]=0.5; Sz[2*mi+1,2*mi+1]=-0.5
    Sp[2*mi,2*mi+1]=1.0
Sp_op=build_op_1body(Sp); Sm_op=Sp_op.T
Sz_op=build_op_1body(Sz)
S2=Sz_op@Sz_op+0.5*(Sp_op@Sm_op+Sm_op@Sp_op)

def singlet_levels(Dq,B,C):
    F4=12.6*C; F2=(441*B+5*F4)/9.0
    V=Vme(F2,F4)
    H=build_op_1body(-4*Dq*spinexpand(P_t2g)+6*Dq*spinexpand(P_eg))+build_op_2body(V)
    H=H.real
    w,_=np.linalg.eigh(H+1e6*S2)
    w=w[w<5e5]
    return np.sort(w)

def groups(w,tol=1.0):
    out=[]
    for x in w:
        if out and abs(x-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([x,1])
    return out
if __name__=="__main__":
    Dq,B=2000.,1000.
    w=singlet_levels(Dq,B,4.5*B)
    g=groups(w)
    print(len(w))
    g0=g[0][0]
    for x,n in g: print(round(x-g0,1),n)
