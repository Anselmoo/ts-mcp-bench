import itertools, numpy as np
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve
from math import pi, sqrt
l=2
# spin-orbitals: (m,s), s=+1/2 idx 0, -1/2 idx 1
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
N=len(orbs)
def G(l1,l2,l3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    return sqrt((2*l1+1)*(2*l2+1)*(2*l3+1)/(4*pi))*float(wigner_3j(l1,l2,l3,0,0,0))*float(wigner_3j(l1,l2,l3,m1,m2,m3))
def ang(k,mi,mk,mj,ml):
    # returns sum_q of angular factor (without 4pi/(2k+1))
    s=0.0
    for q in range(-k,k+1):
        A=(-1)**(mi+q)*G(l,k,l,-mi,-q,mk)
        if A==0: continue
        B=(-1)**mj*G(l,k,l,-mj,q,ml)
        s+=A*B
    return s
def Vspat(mi,mj,mk,ml,F):
    tot=0.0
    for k in (0,2,4):
        a=ang(k,mi,mk,mj,ml)
        tot+=F[k]*4*pi/(2*k+1)*a
    return tot
def build(Dq,B,C):
    F={0:0.0,2:49*B+7*C,4:63*C/5}
    # F0 irrelevant for d-shell constant part? keep (constant shift within d7 only) -> set 0
    V=np.zeros((N,N,N,N))
    for i,(mi,si) in enumerate(orbs):
     for j,(mj,sj) in enumerate(orbs):
      for k,(mk,sk) in enumerate(orbs):
       for ll,(ml,sl) in enumerate(orbs):
        if si!=sk or sj!=sl: continue
        V[i,j,k,ll]=Vspat(mi,mj,mk,ml,F)
    # one-electron: -4Dq + 10Dq P_eg
    h=np.zeros((N,N))
    # eg vectors in complex m basis (spin-independent)
    v0=np.zeros(5); v0[2]=1.0
    vc=np.zeros(5); vc[0]=1/sqrt(2); vc[4]=1/sqrt(2)  # m=-2 index0, m=+2 index4
    P=np.outer(v0,v0)+np.outer(vc,vc)
    hm=-4*Dq*np.eye(5)+10*Dq*P
    for i,(mi,si) in enumerate(orbs):
     for j,(mj,sj) in enumerate(orbs):
      if si==sj: h[i,j]=hm[mi+2,mj+2]
    return h,V
# Build Ms=3/2 determinants: 5 up, 2 down
def dets_ms(nup,ndn):
    up=[i for i,(m,s) in enumerate(orbs) if s>0]
    dn=[i for i,(m,s) in enumerate(orbs) if s<0]
    out=[]
    for a in itertools.combinations(up,nup):
        for b in itertools.combinations(dn,ndn):
            out.append(tuple(sorted(a+b)))
    return out
def matrix(Dq,B,C):
    h,V=build(Dq,B,C)
    dets=dets_ms(5,2)
    idx={d:n for n,d in enumerate(dets)}
    M=np.zeros((len(dets),len(dets)))
    def apply_ann(state,p):
        # a_p on ordered occupied list (sorted); returns (sign,newstate) or None
        if p not in state: return None
        pos=state.index(p)
        return ((-1)**pos, tuple(x for x in state if x!=p))
    def apply_cre(state,p):
        if p in state: return None
        pos=sum(1 for x in state if x<p)
        return ((-1)**pos, tuple(sorted(state+(p,))))
    for n,d in enumerate(dets):
        for c,dd in enumerate(dets):
            pass
    # one-body
    for c,dd in enumerate(dets):
        # a†_i a_j |dd>
        for j in dd:
            r=apply_ann(dd,j)
            if r is None: continue
            s1,st=r
            for i in range(N):
                if h[i,j]==0: continue
                r2=apply_cre(st,i)
                if r2 is None: continue
                s2,st2=r2
                if st2 in idx:
                    M[idx[st2],c]+=s1*s2*h[i,j]
    # two-body: 1/2 sum V_ijkl a†_i a†_j a_l a_k
    for c,dd in enumerate(dets):
        for k in dd:
            r=apply_ann(dd,k)
            if r is None: continue
            s1,st=r
            for ll in st:
                r2=apply_ann(st,ll)
                if r2 is None: continue
                s2,st2=r2
                for j in range(N):
                    for i in range(N):
                        v=V[i,j,k,ll]
                        if v==0: continue
                        r3=apply_cre(st2,j)
                        if r3 is None: continue
                        s3,st3=r3
                        r4=apply_cre(st3,i)
                        if r4 is None: continue
                        s4,st4=r4
                        if st4 in idx:
                            M[idx[st4],c]+=0.5*s1*s2*s3*s4*v
    return M
if __name__=="__main__":
    M=matrix(1000.0,900.0,4000.0)
    ev=np.sort(np.linalg.eigvalsh((M+M.T)/2))
    print(np.round(ev,1))
