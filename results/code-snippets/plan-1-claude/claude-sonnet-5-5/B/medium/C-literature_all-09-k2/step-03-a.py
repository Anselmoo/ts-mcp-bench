import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=range(-2,3)
def c(k,m1,m2):
    return (-1)**m1*5*float(wigner_3j(2,k,2,0,0,0))*float(wigner_3j(2,k,2,-m1,m1-m2,m2))
C3={(k,a,b):c(k,a,b) for k in (0,2,4) for a in ms for b in ms}
orbs=[(m,s) for m in ms for s in (1,-1)]
s=1/np.sqrt(2)
v=lambda d:np.array([d.get(m,0) for m in ms],complex)
z2=v({0:1});x2=v({2:s,-2:s});xy=v({2:-1j*s,-2:1j*s});xz=v({1:s,-1:-s});yz=v({1:1j*s,-1:1j*s})
def Hcf(Dq):
    H=np.zeros((5,5),complex)
    for e in (z2,x2): H+=6*Dq*np.outer(e,e.conj())
    for t in (xy,xz,yz): H+=-4*Dq*np.outer(t,t.conj())
    return H
dets=[d for d in itertools.combinations(range(10),5) if sum(orbs[i][1] for i in d)==3]
idx={d:i for i,d in enumerate(dets)};n=len(dets)
def ann(p,d):
    if p not in d:return None
    i=d.index(p);return (-1)**i,d[:i]+d[i+1:]
def cre(p,d):
    if p in d:return None
    i=sum(1 for x in d if x<p);return (-1)**i,tuple(sorted(d+(p,)))
def build(Dq,B,C):
    F4=441*C/35;F2=49*(B+5*F4/441);F=(0,F2,F4)
    h=Hcf(Dq);H=np.zeros((n,n),complex)
    two=[]
    for a,b,cc,d in itertools.product(orbs,repeat=4):
        if a[0]+b[0]!=cc[0]+d[0] or a[1]!=cc[1] or b[1]!=d[1]:continue
        q=a[0]-cc[0]
        val=sum(Fk*(-1)**q*C3[(k,a[0],cc[0])]*C3[(k,d[0],b[0])] for k,Fk in zip((0,2,4),F))
        if abs(val)>1e-12: two.append((orbs.index(a),orbs.index(b),orbs.index(cc),orbs.index(d),val))
    for d in dets:
        i=idx[d]
        for p in range(10):
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]:continue
                el=h[orbs[p][0]+2,orbs[q][0]+2]
                if abs(el)<1e-12:continue
                r=ann(q,d)
                if not r:continue
                r2=cre(p,r[1])
                if not r2:continue
                H[idx[r2[1]],i]+=el*r[0]*r2[0]
        for a,b,cc,dd,val in two:
            r=ann(cc,d)
            if not r:continue
            r1=ann(dd,r[1])
            if not r1:continue
            r2=cre(b,r1[1])
            if not r2:continue
            r3=cre(a,r2[1])
            if not r3:continue
            H[idx[r3[1]],i]+=0.5*val*r[0]*r1[0]*r2[0]*r3[0]
    return H
def lev(Dq,B,C):
    e=np.linalg.eigvalsh(build(Dq,B,C));e=e-e[0];return e
if __name__=="__main__":
    print(np.round(lev(0,860,3850)[:30]))
    print(10*860+5*3850)
