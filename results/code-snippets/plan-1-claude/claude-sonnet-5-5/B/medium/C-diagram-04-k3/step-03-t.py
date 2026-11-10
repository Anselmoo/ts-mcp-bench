import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=551.;C=2511.
Cn=C/B
F={2:49*(1+Cn/7),4:12.6*Cn}
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.
    return float((-1)**m*5*wigner_3j(2,2,k,0,0,0)*wigner_3j(2,2,k,-m,mp,q))
ms=range(-2,3)
so=[(m,s) for m in ms for s in (0,1)]
idx={x:i for i,x in enumerate(so)}
dets=[d for d in itertools.combinations(range(10),6) if sum(so[i][1] for i in d)==3]
di={d:i for i,d in enumerate(dets)};N=len(dets)
def apply(ops,d):
    s=set(d);sg=1
    for t,i in reversed(ops):
        if t=='a':
            if i not in s: return None
            sg*=(-1)**sum(1 for j in s if j<i); s.remove(i)
        else:
            if i in s: return None
            sg*=(-1)**sum(1 for j in s if j<i); s.add(i)
    return sg,tuple(sorted(s))
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
g={}
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    if m1+m2!=m3+m4: continue
    v=sum(F[k]*CK[(k,m1,m3)]*CK[(k,m4,m2)] for k in (2,4))
    if abs(v)>1e-12: g[(m1,m2,m3,m4)]=v
H2=np.zeros((N,N))
for d in dets:
    j=di[d]
    for (m1,m2,m3,m4),v in g.items():
        for s1 in (0,1):
          for s2 in (0,1):
            r=apply([('c',idx[(m1,s1)]),('c',idx[(m2,s2)]),('a',idx[(m4,s2)]),('a',idx[(m3,s1)])],d)
            if r: H2[di[r[1]],j]+=0.5*v*r[0]
hm=np.zeros((5,5))
for m,val in {0:6,2:1,-2:1,1:-4,-1:-4}.items(): hm[m+2,m+2]=val
hm[0,4]=hm[4,0]=5
H1=np.zeros((N,N))
for d in dets:
    j=di[d]
    for a in range(10):
        for b in range(10):
            if so[a][1]!=so[b][1]: continue
            hv=hm[so[a][0]+2,so[b][0]+2]
            if hv==0: continue
            r=apply([('c',a),('a',b)],d)
            if r: H1[di[r[1]],j]+=hv*r[0]
M=np.zeros((N,N))
for d in dets:
    j=di[d]
    for m in ms:
        for mp in ms:
            r=apply([('c',idx[(m,1)]),('a',idx[(m,0)]),('c',idx[(mp,0)]),('a',idx[(mp,1)])],d)
            if r: M[di[r[1]],j]+=r[0]
c4=np.diag([np.prod([np.exp(-1j*so[i][0]*np.pi/2) for i in d]) for d in dets])
names={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}
allr={}
for x in np.arange(0,4.01,.5):
    Dq=max(x,1e-5)
    H=H2+Dq*H1
    w,v=np.linalg.eigh((H+H.T)/2)
    out=[];i=0
    while i<len(w):
        j=i
        while j+1<len(w) and w[j+1]-w[i]<1e-6: j+=1
        V=v[:,i:j+1];n=j-i+1
        s2=np.trace(V.T@M@V)/n
        mult=int(round(np.sqrt(1+4*s2)))
        ch=np.trace(V.conj().T@c4@V).real
        out.append((w[i],mult,names.get((n,round(ch)),'?%d,%d'%(n,round(ch)))));i=j+1
    e0=out[0][0]
    allr[x]=[(f"{m}{t}",round(e-e0,3)) for e,m,t in out]
    print(x,allr[x][:8])
