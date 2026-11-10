import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (0,1)]
CK={}
for k in (2,4):
  for m1 in ml:
    for m2 in ml:
      CK[k,m1,m2]=float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
def U(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*CK[k,ma,mc]*CK[k,md,mb] for k in (2,4))
dets=[d for d in itertools.combinations(range(10),5) if sum(1 if so[i][1] else -1 for i in d)==3]
idx={d:i for i,d in enumerate(dets)}
def sgnof(nd):
    s=1
    for i in range(len(nd)):
        for j in range(i+1,len(nd)):
            if nd[i]>nd[j]: s=-s
    return s
n=len(dets); HB=np.zeros((n,n));HC=np.zeros((n,n));HD=np.zeros((n,n))
v=np.diag([1.,-4,6,-4,1]); v[0,4]=v[4,0]=5
for I,d in enumerate(dets):
    for i in d:
        for j in range(10):
            if so[j][1]!=so[i][1]: continue
            val=v[ml.index(so[j][0]),ml.index(so[i][0])]
            if val==0 or (j!=i and j in d): continue
            nd=list(d); nd[nd.index(i)]=j
            HD[idx[tuple(sorted(nd))],I]+=val*sgnof(nd)
    for a,b in itertools.combinations(d,2):
        rest=[x for x in d if x not in (a,b)]
        for c,e in itertools.combinations(range(10),2):
            if c in rest or e in rest: continue
            vals=[U(c,e,a,b,F)-U(c,e,b,a,F) for F in ({2:49,4:0},{2:7,4:441/35})]
            if max(abs(x) for x in vals)<1e-12: continue
            nd=list(d); nd[nd.index(a)]=c; nd[nd.index(b)]=e
            s=sgnof(nd); J=idx[tuple(sorted(nd))]
            HB[J,I]+=vals[0]*s; HC[J,I]+=vals[1]*s
def lev(Dq,B,C):
    w=np.linalg.eigvalsh(Dq*HD+B*HB+C*HC); return w-w[0]
def res(p):
    w=lev(*p); return np.array([w[1],w[4],w[7]])-[19240,21890,23000]
for g in ([700,700,3200],[500,600,3400],[300,700,3200]):
    r=least_squares(res,g,diff_step=1e-6); print(r.x, res(r.x)); print(np.round(lev(*r.x)[:12],1))
