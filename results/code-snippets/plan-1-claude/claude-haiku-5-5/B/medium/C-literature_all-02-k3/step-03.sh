mkdir -p /w && cat > /w/d2.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve
l=2
# spin-orbitals: (m,s) index
so=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
N=len(so); idx={x:i for i,x in enumerate(so)}
def ang(k,a,c):
    # <l ma| C^k_q |l mc>, q = mc-ma ... returns dict q->value
    pass
def C(k,q,ma,mc):
    # <l ma|C^k_q|l mc> = (-1)^(l-ma) (l k l; -ma q mc) * <l||C^k||l>, <l||C^k||l> = (-1)^l (2l+1) (l k l;0 0 0)
    if -ma+q!=mc: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-ma)*float(wigner_3j(l,k,l,-ma,q,mc))*red
def Vsp(ma,mb,mc,md,F):
    # <ma mb|1/r12|mc md> spatial = sum_k F^k sum_q (-1)^q <ma|C^k_q|mc><mb|C^k_-q|md>
    tot=0.0
    for k in (0,2,4):
        for q in range(-k,k+1):
            tot+=F[k]*(-1)**q*C(k,q,ma,mc)*C(k,-q,mb,md)
    return tot
# Fock space builder for 2 electrons, 10 spin-orbitals: basis = pairs i<j
basis=list(itertools.combinations(range(N),2))
bi={b:i for i,b in enumerate(basis)}
def build(F,Dq,B=None):
    n=len(basis); H=np.zeros((n,n))
    # one-electron cubic field in m-basis
    # real subspaces: eg = {|0>, (|2>+|-2>)/sqrt2}, t2g = {(|1>+|-1>)/sqrt2, (|1>-|-1>)/sqrt2, (|2>-|-2>)/sqrt2}
    h=np.zeros((5,5))  # index m+2
    eg=[np.eye(5)[2], (np.eye(5)[4]+np.eye(5)[0])/np.sqrt(2)]
    t2=[(np.eye(5)[3]+np.eye(5)[1])/np.sqrt(2),(np.eye(5)[3]-np.eye(5)[1])/np.sqrt(2),(np.eye(5)[4]-np.eye(5)[0])/np.sqrt(2)]
    for v in eg: h+=6*Dq*np.outer(v,v)
    for v in t2: h+=-4*Dq*np.outer(v,v)
    # two-body matrix elements V[a,b,c,d] = <ab|1/r|cd> (spin-orbitals)
    Vt=np.zeros((N,N,N,N))
    for a,(ma,sa) in enumerate(so):
      for b,(mb,sb) in enumerate(so):
        for c,(mc,sc) in enumerate(so):
          for d,(md,sd) in enumerate(so):
            if sa!=sc or sb!=sd: continue
            Vt[a,b,c,d]=Vsp(ma,mb,mc,md,F)
    # operator on 2-electron determinants: H = sum_{ij} h_ij c+_i c_j + 1/2 sum V_abcd c+_a c+_b c_d c_c
    def slater(i,j):
        # determinant |i j> with i<j; apply operators
        return
    occ=lambda st: st
    for I,(p,q) in enumerate(basis):
        # one-body
        for J,(r,s) in enumerate(basis):
            # compute <pq|H|rs> via explicit Slater-Condon using matrix form
            pass
    # generic: build Fock action
    def apply_1(i,j,st):  # c+_i c_j on state (tuple sorted)
        if j not in st: return None
        sgn=1
        lst=list(st)
        pos=lst.index(j); sgn*=(-1)**pos; lst.pop(pos)
        if i in lst: return None
        # insert i
        pos=sum(1 for x in lst if x<i); sgn*=(-1)**pos; lst.insert(pos,i)
        return sgn,tuple(lst)
    def apply_2(a,b,c,d,st): # c+_a c+_b c_d c_c
        r=apply_1(c,c,st) if False else None
        # c_c first
        out=st; sgn=1
        # apply c_c
        if c not in out: return None
        lst=list(out); pos=lst.index(c); sgn*=(-1)**pos; lst.pop(pos); out=tuple(lst)
        if d not in out: return None
        lst=list(out); pos=lst.index(d); sgn*=(-1)**pos; lst.pop(pos); out=tuple(lst)
        if b in out: return None
        pos=sum(1 for x in out if x<b); sgn*=(-1)**pos; lst=list(out); lst.insert(pos,b); out=tuple(lst)
        if a in out: return None
        pos=sum(1 for x in out if x<a); sgn*=(-1)**pos; lst=list(out); lst.insert(pos,a); out=tuple(lst)
        return sgn,tuple(out)
    for J,st in enumerate(basis):
        for I,bra in enumerate(basis):
            val=0.0
            # one-body: sum h_ij c+_i c_j
            for i in range(N):
                for j in range(N):
                    if so[i][1]!=so[j][1]: continue
                    hij=h[so[i][0]+2,so[j][0]+2]
                    if abs(hij)<1e-14: continue
                    r=apply_1(i,j,st)
                    if r and r[1]==bra: val+=hij*r[0]
            for a in range(N):
              for b in range(N):
                for c in range(N):
                  for d in range(N):
                    v=Vt[a,b,c,d]
                    if abs(v)<1e-14: continue
                    r=apply_2(a,b,c,d,st)
                    if r and r[1]==bra: val+=0.5*v*r[0]
            H[I,J]=val
    return H
EOF
cd /w && python3 -c "
from d2 import *
import numpy as np
# free ion check: B,C -> F2=49B+7C, F4=12.6C
def FF(B,C): return {0:0.0,2:49*B+7*C,4:12.6*C}
B,C=1.0,4.0
H=build(FF(B,C),0.0)
ev=np.linalg.eigvalsh(H)
print(np.round(np.unique(np.round(ev,6)),4))
"