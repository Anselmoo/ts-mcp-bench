cat > /tmp/t.py <<'E'
import numpy as np, itertools, sympy
from sympy.physics.wigner import wigner_3j
B=551.;C=2511.
Bn=1.;Cn=C/B
F={2:49*(Bn+Cn/7),4:12.6*Cn}
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.
    return float((-1)**m*5*wigner_3j(2,2,k,0,0,0)*wigner_3j(2,2,k,-m,mp,q))
ms=range(-2,3)
so=[(m,s) for m in ms for s in (0,1)]  # index
idx={x:i for i,x in enumerate(so)}
dets=[d for d in itertools.combinations(range(10),6) if sum(so[i][1] for i in d)==3]
di={d:i for i,d in enumerate(dets)};N=len(dets)
def apply(ops,d):
    # ops list of (type,i) applied right to left; returns (sign,newdet) or None
    s=set(d);l=list(d);sg=1
    for t,i in reversed(ops):
        if t=='a':
            if i not in s: return None
            sg*=(-1)**sum(1 for j in s if j<i); s.remove(i)
        else:
            if i in s: return None
            sg*=(-1)**sum(1 for j in s if j<i); s.add(i)
    return sg,tuple(sorted(s))
def build(Dq):
    H=np.zeros((N,N),complex)
    # one-electron
    h=np.zeros((5,5))
    for m in ms:
        i=m+2
        h[i,i]={0:6,2:1,-2:1,1:-4,-1:-4}[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    # two-electron
    g={}
    for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
        if m1+m2!=m3+m4: continue
        v=sum(F[k]*ck(k,m1,m3)*ck(k,m4,m2) for k in (2,4))
        if abs(v)>1e-12: g[(m1,m2,m3,m4)]=v
    for d in dets:
        j=di[d]
        for a in range(10):
            for b in range(10):
                hv=h[so[a][0]+2,so[b][0]+2] if so[a][1]==so[b][1] else 0
                if hv==0: continue
                r=apply([('c',a),('a',b)],d)
                if r: H[di[r[1]],j]+=hv*r[0]
        for (m1,m2,m3,m4),v in g.items():
            for s1 in (0,1):
              for s2 in (0,1):
                a=idx[(m1,s1)];b=idx[(m2,s2)];c=idx[(m3,s1)];dd=idx[(m4,s2)]
                r=apply([('c',a),('c',b),('a',dd),('a',c)],d)
                if r: H[di[r[1]],j]+=0.5*v*r[0]
    return H
# S^2 = S-S+ + Sz(Sz+1), Sz=0
def S2():
    M=np.zeros((N,N))
    for d in dets:
        j=di[d]
        for m in ms:
            for mp in ms:
                # S- S+ = sum a†_{m dn} a_{m up} a†_{mp up} a_{mp dn}
                r=apply([('c',idx[(m,1)]),('a',idx[(m,0)]),('c',idx[(mp,0)]),('a',idx[(mp,1)])],d)
                if r: M[di[r[1]],j]+=r[0]
    return M
S2m=S2()
c4=np.diag([np.prod([np.exp(-1j*so[i][0]*np.pi/2) for i in d]) for d in dets])
def levels(Dq):
    H=build(Dq)
    w,v=np.linalg.eigh((H+H.conj().T)/2)
    out=[];i=0
    while i<len(w):
        j=i
        while j+1<len(w) and w[j+1]-w[i]<1e-6*1+1e-5: j+=1
        V=v[:,i:j+1];n=j-i+1
        s2=np.trace(V.conj().T@S2m@V).real/n
        S=round((-1+np.sqrt(1+4*s2))/2) if False else None
        Sv=(-1+np.sqrt(1+4*s2))/2;mult=int(round(2*Sv+1))
        ch=np.trace(V.conj().T@c4@V).real
        out.append((w[i],mult,n,round(ch)));i=j+1
    return out
import json
names={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}
res=[]
for x in np.arange(0,4.01,.5):
    Dq=max(x,1e-3)
    L=levels(Dq)
    L=[(e,names.get((n,ch),'?%d,%d'%(n,ch)),m) for e,m,n,ch in L]
    e0=L[0][0]
    print(x,[(f"{m}{t}",round(e-e0,3)) for e,t,m in L[:9]])
E
python3 /tmp/t.py