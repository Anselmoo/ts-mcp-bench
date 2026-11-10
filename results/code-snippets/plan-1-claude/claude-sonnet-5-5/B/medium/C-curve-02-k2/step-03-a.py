import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt,pi,N
B=722.;C=3003.
Bn=1.;Cn=C/B
M=np.array([[9,-5],[5,34]])/441.
F2,F4=np.linalg.solve(M,[Bn,Cn])
F={2:F2,4:F4}
ms=[-2,-1,0,1,2]
def ck(k,a,c):
    if abs(a-c)>k: return 0.
    return float(N(sqrt(4*pi/(2*k+1))*(-1)**a*gaunt(2,k,2,-a,a-c,c)))
c={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
n=10
def V(Dq):
    h=np.zeros((5,5))
    for i,m in enumerate(ms):
        h[i,i]={2:1,1:-4,0:6,-1:-4,-2:1}[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    return h
dets=[d for d in itertools.combinations(range(n),3)]
idx={d:i for i,d in enumerate(dets)}
def apply(ops,d):
    # ops list of (type,orb) applied right to left
    st=list(d);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return None
            p=st.index(o);sign*=(-1)**p;st.pop(p)
        else:
            if o in st: return None
            p=sum(1 for x in st if x<o);sign*=(-1)**p;st.insert(p,o)
    return tuple(st),sign
def build(Dq):
    H=np.zeros((120,120));h=V(Dq)
    for D in dets:
        j=idx[D]
        for p in range(n):
            for q in range(n):
                if so[p][1]!=so[q][1]: continue
                v=h[so[p][0]+2,so[q][0]+2]
                if v==0: continue
                r=apply([('c',p),('a',q)],D)
                if r: H[idx[r[0]],j]+=v*r[1]
        for p,q,r_,s in itertools.product(range(n),repeat=4):
            (a,sa),(b,sb),(cc,sc),(d,sd)=so[p],so[q],so[r_],so[s]
            if sa!=sc or sb!=sd or a+b!=cc+d: continue
            val=sum(c[(k,a,cc)]*c[(k,d,b)]*F[k] for k in (2,4))
            if val==0: continue
            r=apply([('c',p),('c',q),('a',s),('a',r_)],D)
            if r: H[idx[r[0]],j]+=0.5*val*r[1]
    return H
# S^2
def S2():
    S=np.zeros((120,120))
    Sz=np.array([ (sum(1 if so[o][1]==0 else -1 for o in D))/2 for D in dets])
    S+=np.diag(Sz*Sz+Sz)
    for D in dets:
        j=idx[D]
        for m in ms:
            r=apply([('c',so[0][0] and 0)],D) if False else None
        # S-S+ : sum over m,m'
        for m in ms:
            for m2 in ms:
                p=so.index((m,1));q=so.index((m,0));p2=so.index((m2,0));q2=so.index((m2,1))
                # S-S+ = sum a†_{m,down}a_{m,up} a†_{m2,up}a_{m2,down}... 
                pass
    return None
for Dq in (1.0,2.2,3.5):
    H=build(Dq)
    w,U=np.linalg.eigh(H)
    # group
    g=[];
    for e in w:
        if g and abs(e-g[-1][0])<1e-6: g[-1][1]+=1
        else: g.append([e,1])
    print(Dq,[(round(e-g[0][0],3),d) for e,d in g[:8]])
