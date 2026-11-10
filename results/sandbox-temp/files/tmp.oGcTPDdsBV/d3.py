import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq, fsolve
l=2; ms=list(range(-2,3))
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(2*l+1)*gaunt(l,k,l,-m1,m1-m2,m2))
Ck={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
spin=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def g(a,b,c,d,F):  # <ab|1/r|cd>, spin orbitals
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[spin[x] for x in (a,b,c,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(F[k]*Ck[(k,ma,mc)]*Ck[(k,md,mb)] for k in (2,4))
def H(Dq,B,Cr):
    F={2:49*(B+Cr/7),4:441*Cr/35}
    h=np.zeros((5,5))
    for m in ms: h[m+2,m+2]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    N=len(dets); M=np.zeros((N,N))
    # build via second quantization
    def apply(ops,det):
        st=list(det); sign=1
        for (typ,o) in reversed(ops):
            if typ=='a':
                if o not in st: return None,0
                p=st.index(o); sign*=(-1)**p; st.pop(p)
            else:
                if o in st: return None,0
                st.insert(0,o); 
                # sort
                p=sorted(st).index(o); sign*=(-1)**p; st=sorted(st)
        return tuple(st),sign
    for d in dets:
        j=idx[d]
        for p in range(10):
            for q in range(10):
                if spin[p][1]!=spin[q][1]: continue
                v=h[spin[p][0]+2,spin[q][0]+2]
                if v==0: continue
                r,s=apply([('c',p),('a',q)],d)
                if r: M[idx[r],j]+=s*v
        for p in range(10):
         for q in range(10):
          for r_ in range(10):
           for s_ in range(10):
            v=g(p,q,r_,s_,F)
            if abs(v)<1e-12: continue
            r,s=apply([('c',p),('c',q),('a',s_),('a',r_)],d)
            if r: M[idx[r],j]+=0.5*s*v
    return M
Sz=np.array([sum(1 if spin[o][1]==0 else -1 for o in d)/2 for d in dets])
def levels(Dq,B,Cr):
    M=H(Dq,B,Cr); E=np.linalg.eigvalsh(M); E=E-E[0]
    # group
    out=[];i=0
    while i<len(E):
        j=i
        while j<len(E) and E[j]-E[i]<1e-3: j+=1
        out.append((round(E[i],1),j-i)); i=j
    return out
import sys
print(levels(2155,657.4,4*657.4)[:8])
