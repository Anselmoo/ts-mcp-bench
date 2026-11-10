cat > $TMPDIR/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=821.;C=3657.
def run(N,Dq):
    F4=C/35;F2=B+5*F4;Fs={2:49*F2,4:441*F4}
    ms=[-2,-1,0,1,2]
    def ck(m1,m2,k):
        q=m1-m2
        if abs(q)>k: return 0.
        return float(gaunt(2,k,2,-m1,q,m2)*(-1)**m1*np.sqrt(4*np.pi/(2*k+1)))
    def g(a,b,c,d):
        if a+b!=c+d: return 0.
        return sum(ck(a,c,k)*ck(d,b,k)*Fs[k] for k in (2,4))
    idx={m:i for i,m in enumerate(ms)}
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[idx[m]]=c
        return v
    s=2**-.5
    eg=[vec({0:1}),vec({2:s,-2:s})]
    t2=[vec({2:s,-2:-s}),vec({1:1}),vec({-1:1})]
    h=sum(-6*Dq*np.outer(v,v.conj()) for v in eg)+sum(4*Dq*np.outer(v,v.conj()) for v in t2)
    so=[(m,s_) for s_ in (0,1) for m in ms]
    n=10
    H1=np.zeros((n,n),complex)
    for i,(m,s_) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s_==s2:H1[i,j]=h[idx[m],idx[m2]]
    G=np.zeros((n,n,n,n))
    for a,(ma,sa) in enumerate(so):
     for b,(mb,sb) in enumerate(so):
      for c,(mc,sc) in enumerate(so):
       for d,(md,sd) in enumerate(so):
        if sa==sc and sb==sd: G[a,b,c,d]=g(ma,mb,mc,md)
    dets=list(itertools.combinations(range(n),N));di={d:i for i,d in enumerate(dets)}
    def ap(op,det,create):
        l=list(det)
        if create:
            if op in l:return None
            pos=sum(1 for x in l if x<op);l.insert(pos,op);return tuple(l),(-1)**pos
        if op not in l:return None
        pos=l.index(op);l.pop(pos);return tuple(l),(-1)**pos
    H=np.zeros((len(dets),len(dets)),complex)
    S2=np.zeros_like(H)
    for j,dt in enumerate(dets):
        for p in range(n):
         for q in range(n):
            if abs(H1[p,q])<1e-12:continue
            r=ap(q,dt,False)
            if r is None:continue
            r2=ap(p,r[0],True)
            if r2 is None:continue
            H[di[r2[0]],j]+=H1[p,q]*r[1]*r2[1]
        for c in range(n):
         for d in range(n):
          r=ap(c,dt,False)
          if r is None:continue
          r1=ap(d,r[0],False)
          if r1 is None:continue
          sg=r[1]*r1[1]
          for a in range(n):
           for b in range(n):
            gv=G[a,b,c,d]
            if abs(gv)<1e-12:continue
            r2=ap(b,r1[0],True)
            if r2 is None:continue
            r3=ap(a,r2[0],True)
            if r3 is None:continue
            H[di[r3[0]],j]+=0.5*gv*sg*r2[1]*r3[1]
        # S2 = S-S+ + Sz^2+Sz ; S+ = sum a†(m,up) a(m,down) ; up index 5+
        nu=sum(1 for x in dt if x>=5);nd=N-nu;sz=(nu-nd)/2
        S2[j,j]+=sz*sz+sz
        for m in range(5):
            r=ap(m,dt,False)   # annihilate down(m)
            if r is None:continue
            r2=ap(5+m,r[0],True)
            if r2 is None:continue
            d1=r2[0];ph=r[1]*r2[1]
            # apply S-: a†(down m') a(up m')
            for m2 in range(5):
                t=ap(5+m2,d1,False)
                if t is None:continue
                t2_=ap(m2,t[0],True)
                if t2_ is None:continue
                S2[di[t2_[0]],j]+=ph*t[1]*t2_[1]
    return H,S2
H,S2=run(2,0.0);e=np.linalg.eigvalsh(H);print(sorted(set(np.round(e-e[0],1)))[:4],B)
for x in (0.90,2.15,3.35):
    H,S2=run(4,x*B)
    w,v=np.linalg.eigh(H+1e-3*S2)
    sp=np.einsum('ij,ik,kj->j',v.conj(),S2,v).real
    w=np.einsum('ij,ik,kj->j',v.conj(),H,v).real
    w=w-w.min()
    lv=[]
    for a,b in zip(w,sp):
        if not lv or abs(a-lv[-1][0])>1e-2 or abs(b-lv[-1][1])>.1: lv.append([a,b,1])
        else: lv[-1][2]+=1
    print(x,[(round(a/B,3),round(2*(0.5+(1+4*b)**.5/2-0.5)),k) for a,b,k in lv[:8]])
E
python3 $TMPDIR/a.py