import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import sqrt
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*5*gaunt(2,k,2,-m1,q,m2))
C={(k,a,b):c(k,a,b) for k in(2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in(0,1)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
pairs=[(a,b,cc,d) for a in range(10) for b in range(10) for cc in range(10) for d in range(10) if so[a][1]==so[cc][1] and so[b][1]==so[d][1] and so[a][0]+so[b][0]==so[cc][0]+so[d][0]]
i5=lambda m:ms.index(m)
def mk(B,Cc,Dq):
    F4=Cc/35;F2=B+5*F4
    V={}
    for (a,b,cc,d) in pairs:
        ma,mb,mc,md=so[a][0],so[b][0],so[cc][0],so[d][0]
        V[(a,b,cc,d)]=F2*C[(2,ma,mc)]*C[(2,md,mb)]+F4*C[(4,ma,mc)]*C[(4,md,mb)]
    vecs=[];en=[]
    def vec(d):
        e=np.zeros(5);
        for m,x in d.items(): e[i5(m)]=x
        return e
    s=1/sqrt(2)
    vecs=[vec({0:1}),vec({2:s,-2:s}),vec({2:s,-2:-s}),vec({1:s,-1:-s}),vec({1:s,-1:s})]
    en=[6*Dq,6*Dq,-4*Dq,-4*Dq,-4*Dq]
    W=np.array(vecs).T;h5=(W*np.array(en))@W.T
    h=np.zeros((10,10))
    for a,(ma,sa) in enumerate(so):
     for b,(mb,sb) in enumerate(so):
      if sa==sb:h[a,b]=h5[i5(ma),i5(mb)]
    return V,h
def lev(B,Cc,Dq):
    V,h=mk(B,Cc,Dq)
    n=len(dets);M=np.zeros((n,n))
    for j,d in enumerate(dets):
        ds=set(d)
        for q in d:
          for p in range(10):
            if h[p,q]==0: continue
            if p!=q and p in ds: continue
            l=[x for x in d if x!=q]; s=(-1)**d.index(q)
            l.insert(0,0); l=l[1:]
            l2=sorted(l+[p]); s*=(-1)**l2.index(p)
            M[idx[tuple(l2)],j]+=s*h[p,q]
        for c1 in d:
         for d1 in d:
          if c1==d1: continue
          l=list(d); s=(-1)**l.index(c1); l.remove(c1)
          s*=(-1)**l.index(d1); l.remove(d1)
          for (a,b,cc,dd),v in []: pass
        # two-body via pairs
        for (a,b,cc,dd),v in V.items():
          if v==0 or cc not in ds or dd not in ds or cc==dd: continue
          l=list(d); s=(-1)**l.index(cc); l.remove(cc)
          s*=(-1)**l.index(dd); l.remove(dd)
          if b in l or a in l or a==b: continue
          s*=(-1)**sum(1 for x in l if x<b); l.append(b); l.sort()
          s*=(-1)**sum(1 for x in l if x<a); l.append(a); l.sort()
          M[idx[tuple(l)],j]+=0.5*v*s
    assert np.allclose(M,M.T)
    w=np.linalg.eigvalsh(M)
    return w
def bands(B,Cc,Dq):
    w=lev(B,Cc,Dq);w=w-w[0]
    return w
if __name__=="__main__":
    w=bands(900,4000,1000)
    u=[];
    for x in w:
        if not u or abs(x-u[-1][0])>1: u.append([x,1])
        else: u[-1][1]+=1
    print([(round(a),b) for a,b in u[:14]])
