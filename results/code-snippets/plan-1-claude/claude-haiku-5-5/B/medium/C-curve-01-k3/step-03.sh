cd /tmp/tsbench-run-xtj98wvz 2>/dev/null || cd /; pwd; cat << 'EOF' | python3 -
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2; ms=list(range(-2,3))
def C(k,q,m,mp):
    if m!=mp+q: return 0.0
    return (-1)**(l-m)*float(wigner_3j(l,k,l,-m,q,mp))*(2*l+1)
def ang(k,a,c,b,d):
    return sum(C(k,q,a,c)*C(k,-q,b,d) for q in range(-k,k+1))
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
def run(Cc, Dqs, nel=4, B=1.0):
    F4=441*Cc/35; F2=441*B+5*F4
    Fk={2:F2,4:F4}
    states=list(itertools.combinations(range(10),nel)); idx={s:i for i,s in enumerate(states)}
    N=len(states)
    def apply_pair(st,p,q,r,s_):
        occ=list(st); sign=1
        if r not in occ: return None,0
        pos=occ.index(r); sign*=(-1)**pos; occ.pop(pos)
        if s_ not in occ: return None,0
        pos=occ.index(s_); sign*=(-1)**pos; occ.pop(pos)
        if q in occ: return None,0
        pos=sum(1 for x in occ if x<q); sign*=(-1)**pos; occ.insert(pos,q)
        if p in occ: return None,0
        pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
        return tuple(occ),sign
    Hee=np.zeros((N,N))
    for k in (2,4):
     for p in range(10):
      for q in range(10):
       for r in range(10):
        for s_ in range(10):
          mp,sp=orbs[p]; mq,sq=orbs[q]; mr,sr=orbs[r]; mss,ss=orbs[s_]
          if sp!=sr or sq!=ss: continue
          val=ang(k,mp,mr,mq,mss)
          if abs(val)<1e-14: continue
          for ci,st in enumerate(states):
            new,sg=apply_pair(st,p,q,r,s_)
            if new is None: continue
            Hee[idx[new],ci]+=0.5*Fk[k]*val*sg
    diag={-2:1,-1:-4,0:6,1:-4,2:1}
    one=np.zeros((10,10))
    for i,(m,s) in enumerate(orbs): one[i,i]=diag[m]
    for i,(m,s) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            if s==s2 and ((m==2 and m2==-2) or (m==-2 and m2==2)): one[i,j]=5
    H1=np.zeros((N,N))
    for ci,st in enumerate(states):
        for p in range(10):
            for r in range(10):
                if one[p,r]==0: continue
                occ=list(st)
                if r not in occ: continue
                pos=occ.index(r); sg=(-1)**pos; occ.pop(pos)
                if p in occ: continue
                pos=sum(1 for x in occ if x<p); sg*=(-1)**pos; occ.insert(pos,p)
                H1[idx[tuple(occ)],ci]+=one[p,r]*sg
    # S^2
    Sz=np.zeros(N); 
    S2=np.zeros((N,N))
    # S^2 = Sz^2 + (S+S- + S-S+)/2 ; build via spin-orbital ops
    def sp_ops():
        Sp=np.zeros((N,N)); Sm=np.zeros((N,N))
        for ci,st in enumerate(states):
            for a in range(10):
                for b in range(10):
                    ma,sa=orbs[a]; mb,sb=orbs[b]
                    if ma!=mb: continue
                    if sa==-0.5 and sb==0.5: target=('p')
                    else: continue
                    # S+ = sum a+_{up} a_{down}
                    occ=list(st)
                    if b not in occ or a in occ: continue
                    pos=occ.index(b); sg=(-1)**pos; occ.pop(pos)
                    pos=sum(1 for x in occ if x<a); sg*=(-1)**pos; occ.insert(pos,a)
                    Sp[idx[tuple(occ)],ci]+=sg
        return Sp
    Sp=sp_ops(); Sm=Sp.T
    Sz=np.zeros((N,N))
    for ci,st in enumerate(states):
        Sz[ci,ci]=sum(0.5 if orbs[x][1]>0 else -0.5 for x in st)
    S2=Sm@Sp+Sz@Sz+Sz  # S-S+ = S^2 - Sz^2 - Sz ; S^2 = S-S+ + Sz^2 + Sz
    # careful: S^2 = S- S+ + Sz^2 + Sz
    S2=Sm@Sp+Sz@Sz+Sz
    out={}
    for Dq in Dqs:
        H=Hee+Dq*H1
        w,v=np.linalg.eigh(H)
        # group
        s2=np.diag(v.T@S2@v)
        out[Dq]=(w,s2)
    return out
import sys
# test d2: ground 3F, 3P relative
r=run(Cc=0.0,Dqs=[0.0],nel=2)
w,s2=r[0.0]
vals=sorted(set(np.round(w,6)))
print("d2 levels (B=1,C=0):",[(v, round(float(np.mean(s2[np.abs(w-v)<1e-6])),2), int(np.sum(np.abs(w-v)<1e-6))) for v in vals])
EOF