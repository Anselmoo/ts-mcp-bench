import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
def apply(ops,occ):
    occ=list(occ); sign=1
    for o,cr in reversed(ops):
        n=sum(1 for x in occ if x<o)
        if cr:
            if o in occ: return None
            occ.append(o); occ.sort()
        else:
            if o not in occ: return None
            occ.remove(o)
        sign*=(-1)**n
    return sign,tuple(occ)
def blocks(nup):
    dets=[d for d in itertools.combinations(range(10),6) if sum(so[o][1]==0 for o in d)==nup]
    idx={d:i for i,d in enumerate(dets)}
    n=len(dets)
    Hdq=np.zeros((n,n)); H2=np.zeros((n,n)); H4=np.zeros((n,n))
    h=np.zeros((5,5))
    for i,m in enumerate(ms): h[i,i]={0:6,1:-4,2:1}[abs(m)]
    h[0,4]=h[4,0]=5
    for I,D in enumerate(dets):
        for p in range(10):
            for q in D:
                if so[p][1]!=so[q][1]: continue
                v=h[ms.index(so[p][0]),ms.index(so[q][0])]
                if v==0: continue
                r=apply([(p,1),(q,0)],D)
                if r: Hdq[idx[r[1]],I]+=r[0]*v
        for p in range(10):
         for q in range(10):
          for r_ in D:
           for s in D:
            if so[p][1]!=so[r_][1] or so[q][1]!=so[s][1]: continue
            a,b,c,d=so[p][0],so[q][0],so[r_][0],so[s][0]
            if a+b!=c+d: continue
            r=apply([(p,1),(q,1),(s,0),(r_,0)],D)
            if not r: continue
            H2[idx[r[1]],I]+=0.5*r[0]*CK[(2,a,c)]*CK[(2,d,b)]
            H4[idx[r[1]],I]+=0.5*r[0]*CK[(4,a,c)]*CK[(4,d,b)]
    return Hdq,H2,H4
b0=blocks(3); b1=blocks(4)
def levels(Dq,B,C):
    F4=C*441/35; F2=49*(B+5*F4/441)
    out=[]
    for bl in (b0,b1):
        H=Dq*bl[0]+F2*bl[1]+F4*bl[2]
        out.append(np.round(np.linalg.eigvalsh(H),4))
    e0,e1=out
    l0=list(e0)
    for x in e1:
        j=np.argmin(np.abs(np.array(l0)-x)); l0.pop(j)
    l0=np.array(sorted(l0))
    g=[]
    for x in l0:
        if g and abs(g[-1][0]-x)<1e-2: g[-1][1]+=1
        else: g.append([x,1])
    E0=min(e0.min(),e1.min())
    return [(round(x-g[0][0],1),d) for x,d in g], round(g[0][0]-E0,1)
def bands(Dq,B):
    g,_=levels(Dq,B,4.5*B)
    return g
print(levels(1643,548.75,2469)[0][:8])
obs=np.array([13960,22740,29700])
def res(p):
    g=bands(*p); e=[x for x,d in g if d==3][:3]
    return np.array(e)-obs
s=least_squares(res,[1643,550],diff_step=1e-3); print(s.x,res(s.x))
print(levels(s.x[0],s.x[1],4.5*s.x[1]))
