import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]  # index = 2*(m+2)+(s>0?0:1)
N=len(orbs)
def ck(k,ma,mc):  # <ma|C^k_q|mc> returns dict q->value
    out={}
    for q in range(-k,k+1):
        if ma!=mc+q and True: pass
        m_a=ma; m_c=mc
        # <l m_a|C^k_q|l m_c> nonzero if m_a = m_c + q
        if m_a-m_c!=q: continue
        # formula (-1)^{l-m}(l k l; -m q m') * (-1)^l (2l+1)(l k l;000)
        val=(-1)**(l-m_a)*float(wigner_3j(l,k,l,-m_a,q,m_c))*(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
        out[q]=val
    return out
def V(k,ma,mb,mc,md):
    # <ma mb|1/r12|mc md> angular factor for each k (coefficient of F_k)
    tot=0.0
    for q in range(-k,k+1):
        # (-1)^q <ma|C^k_{-q}|mc><mb|C^k_q|md>
        A=ck(k,ma,mc).get(-q,0.0); B=ck(k,mb,md).get(q,0.0)
        tot+=(-1)**q*A*B
    return tot
# build Coulomb tensor g[a,b,c,d] = sum_k F_k * ang_k * spin deltas
ang={k:np.zeros((N,N,N,N)) for k in (0,2,4)}
for a,(ma,sa) in enumerate(orbs):
 for b,(mb,sb) in enumerate(orbs):
  for c,(mc,sc) in enumerate(orbs):
   for d,(md,sd) in enumerate(orbs):
    if sa!=sc or sb!=sd: continue
    for k in (0,2,4):
        ang[k][a,b,c,d]=V(k,ma,mb,mc,md)
# fermion many-body basis
states=[s for s in itertools.combinations(range(N),5)]
idx={s:i for i,s in enumerate(states)}
def apply_ops(occ,ops):
    # ops list applied right-to-left: ops = [(type,orb)], type 'c' or 'a'
    occ=list(occ); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return tuple(sorted(occ)),sign
def build(F):
    D=len(states)
    H=np.zeros((D,D))
    # one-body: h = -4Dq + 10Dq*P_eg in complex basis; handled separately
    # two-body: H = 1/2 sum g_abcd a^+_a a^+_b a_d a_c
    for i,s in enumerate(states):
        for a in range(N):
          for b in range(N):
            for c in range(N):
              for d in range(N):
                val=sum(F[k]*ang[k][a,b,c,d] for k in (0,2,4))
                if abs(val)<1e-14: continue
                if a==b or c==d: continue
                nocc,sg=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
                if nocc is None: continue
                H[idx[nocc],i]+=0.5*val*sg
    return H
def onebody(Dq):
    # eg: m=0 and (|2>+|-2>)/sqrt2, spin-independent
    eg=np.zeros(N,complex)
    # orbital vectors
    vecs={}
    def ov(m): return m
    P=np.zeros((5,5))
    # build projector in m basis
    v0=np.zeros(5); v0[2]=1
    v2=np.zeros(5); v2[4]=1/np.sqrt(2); v2[0]=1/np.sqrt(2)
    Peg=np.outer(v0,v0)+np.outer(v2,v2)
    h5=-4*Dq*np.eye(5)+10*Dq*Peg
    h=np.zeros((N,N))
    for a,(ma,sa) in enumerate(orbs):
     for b,(mb,sb) in enumerate(orbs):
      if sa==sb: h[a,b]=h5[ma+2,mb+2]
    return h
def hfull(Dq,B,C):
    F4=35*C/ (35) *0  # placeholder
    F4=C*441/35.0
    F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    H=build(F)
    h=onebody(Dq)
    # one body: sum h_ab a+_a a_b
    D=len(states)
    H1=np.zeros((D,D))
    for i,s in enumerate(states):
        for a in range(N):
          for b in range(N):
            if abs(h[a,b])<1e-14: continue
            nocc,sg=apply_ops(s,[('c',a),('a',b)])
            if nocc is None: continue
            H1[idx[nocc],i]+=h[a,b]*sg
    return H+H1
import sys
np.save('/tmp/dummy.npy',np.zeros(1))
