import numpy as np, itertools, json
from sympy.physics.wigner import gaunt
from sympy import N
B=1.0;C=3660/859
F={2:49*B+7*C,4:63*C/5}
ms=[-2,-1,0,1,2]
def ckk(a,c,k):
    q=a-c
    if abs(q)>k: return 0.0
    return float(N(gaunt(2,k,2,-a,q,c)))*(-1)**a*np.sqrt(4*np.pi/(2*k+1))
orbs=[(m,s) for m in ms for s in (0,1)]
def g(a,b,c,d):
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]: return 0
    return sum(F[k]*ckk(a[0],c[0],k)*ckk(d[0],b[0],k) for k in (2,4))
G={}
for a,b,c,d in itertools.product(range(10),repeat=4):
    v=g(orbs[a],orbs[b],orbs[c],orbs[d])
    if abs(v)>1e-12: G[(a,b,c,d)]=v
def ann(det,i):
    if not det>>i&1: return None
    return det^(1<<i),(-1)**bin(det&((1<<i)-1)).count('1')
def cr(det,i):
    if det>>i&1: return None
    return det|(1<<i),(-1)**bin(det&((1<<i)-1)).count('1')
def run(Dq,Ms2):
    dets=[sum(1<<i for i in c) for c in itertools.combinations(range(10),7) if sum(1 if orbs[i][1]==0 else -1 for i in c)==Ms2]
    idx={d:i for i,d in enumerate(dets)};n=len(dets);H=np.zeros((n,n))
    V={0:6*Dq,1:-4*Dq,-1:-4*Dq,2:Dq,-2:Dq}
    for d in dets:
        j=idx[d]
        for p in range(10):
            for q in range(10):
                o1,o2=orbs[p],orbs[q]
                if o1[1]!=o2[1]: continue
                if o1[0]==o2[0]: v=V[o1[0]]
                elif abs(o1[0]-o2[0])==4: v=5*Dq
                else: continue
                r=ann(d,q)
                if r is None: continue
                r2=cr(r[0],p)
                if r2 is None: continue
                H[idx[r2[0]],j]+=v*r[1]*r2[1]
        for (a,b,c,dd),v in G.items():
            r=ann(d,dd)
            if r is None: continue
            r1=ann(r[0],c)
            if r1 is None: continue
            r2=cr(r1[0],b)
            if r2 is None: continue
            r3=cr(r2[0],a)
            if r3 is None: continue
            H[idx[r3[0]],j]+=0.5*v*r[1]*r1[1]*r2[1]*r3[1]
    w,U=np.linalg.eigh(H)
    ph=np.array([np.exp(-1j*np.pi/2*sum(orbs[i][0] for i in range(10) if d>>i&1)) for d in dets])
    return w,U,ph
def levels(Dq):
    w3,_,_=run(Dq,3); w,U,ph=run(Dq,1)
    cl=[];i=0
    while i<len(w):
        j=i
        while j+1<len(w) and w[j+1]-w[i]<1e-6: j+=1
        cl.append((i,j));i=j+1
    out=[]
    for i,j in cl:
        dim=j-i+1;S=4 if any(abs(w[i]-x)<1e-6 for x in w3) else 2
        chi=sum(U[:,k].conj()@(ph*U[:,k]) for k in range(i,j+1)).real
        ir={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}[(dim,int(round(chi)))]
        out.append((w[i],f"{S}{ir}g"))
    return out
res=[]
for x in np.arange(0,4.01,.5):
    L=levels(max(x,1e-4))
    e0=L[0][0]; L=[(e-e0,t) for e,t in L][:6]
    print(x,[(t,round(e,3)) for e,t in L])
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
xs=np.linspace(0.02,4,50);Y=[]
for x in xs:
    L=levels(x);e0=L[0][0];Y.append([e-e0 for e,t in L][:12])
Y=np.array(Y)
for k in range(Y.shape[1]):plt.plot(xs,Y[:,k])
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.savefig('diagram.png')
