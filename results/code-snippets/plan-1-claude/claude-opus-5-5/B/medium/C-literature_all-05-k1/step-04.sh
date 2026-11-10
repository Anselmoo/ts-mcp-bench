
cd $(mktemp -d) && cat << 'EOF' > d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
l=2; ms=list(range(-2,3))
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(l,k,l,-m1,m1-m2,m2))
Ck={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
spin=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
G={}
for a,b,c,d in itertools.product(range(10),repeat=4):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[spin[x] for x in (a,b,c,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    G[(a,b,c,d)]=(Ck[(2,ma,mc)]*Ck[(2,md,mb)],Ck[(4,ma,mc)]*Ck[(4,md,mb)])
def apply(ops,det):
    st=list(det); sign=1
    for (typ,o) in reversed(ops):
        if typ=='a':
            if o not in st: return None,0
            p=st.index(o); sign*=(-1)**p; st.pop(p)
        else:
            if o in st: return None,0
            st=sorted(st+[o]); sign*=(-1)**st.index(o)
    return tuple(st),sign
N=len(dets)
M2=np.zeros((N,N));M4=np.zeros((N,N));MD=np.zeros((N,N))
h=np.zeros((5,5))
for m in ms: h[m+2,m+2]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
h[0,4]=h[4,0]=5
for d in dets:
    j=idx[d]
    for p in range(10):
        for q in range(10):
            if spin[p][1]!=spin[q][1]: continue
            v=h[spin[p][0]+2,spin[q][0]+2]
            if v==0: continue
            r,s=apply([('c',p),('a',q)],d)
            if r: MD[idx[r],j]+=s*v
    for (p,q,r_,s_),(v2,v4) in G.items():
        r,s=apply([('c',p),('c',q),('a',s_),('a',r_)],d)
        if r: M2[idx[r],j]+=0.5*s*v2; M4[idx[r],j]+=0.5*s*v4
def levels(Dq,B,Cr):
    M=Dq*MD+49*(B+Cr/7)*M2+441*Cr/35*M4
    E=np.linalg.eigvalsh(M); E=E-E[0]
    out=[];i=0
    while i<len(E):
        j=i
        while j<len(E) and E[j]-E[i]<1e-3: j+=1
        out.append((round(E[i],1),j-i)); i=j
    return out
print(levels(0,1000,4000)[:6])
print(levels(2155,657.4,4*657.4)[:8])
def f(x):
    Dq,B,Cr=x; L=levels(Dq,B,Cr)
    d={}
    for e,g in L[1:]:
        d.setdefault(g,[]).append(e)
    return [d[12][0]-21550, d[4][0]-15200, None]
def res(x):
    Dq,B,Cr=x; L=levels(Dq,B,Cr)
    q=[e for e,g in L if g==12]; e2=[e for e,g in L[1:] if g==4]
    # quartet T: 12-fold; 2E: 4-fold; but doublets T 6-fold
    return [q[0]-21550,q[1]-28500,e2[0]-15200]
sol=fsolve(res,[2155,657,2600]); print(sol, res(sol)); print(levels(*sol)[:8], sol[2]/sol[1])
EOF
python3 d3.py