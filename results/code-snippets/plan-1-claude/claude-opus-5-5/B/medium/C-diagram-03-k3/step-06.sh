cat > ts.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=806.;C=3570.
F={0:0.,2:49*B+7*C,4:441*C/35}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
orbs=[(m,s) for m in ms for s in (1,-1)]
def V2(a,b,c,d):
    if a[1]!=c[1] or b[1]!=d[1]: return 0.
    if a[0]+b[0]!=c[0]+d[0]: return 0.
    return sum(ck(k,a[0],c[0])*ck(k,d[0],b[0])*F[k] for k in (0,2,4))
def cf(m1,m2):
    if m1==m2: return {0:6,1:-4,-1:-4,2:1,-2:1}[m1]
    if abs(m1-m2)==4: return 5
    return 0.
idx=range(10)
dets=[d for d in itertools.combinations(idx,5) if sum(orbs[i][1] for i in d)==1]
n=len(dets); pos={d:i for i,d in enumerate(dets)}
def app(det,ops):
    st=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return None
            k=st.index(o); sign*=(-1)**k; st.pop(k)
        else:
            if o in st: return None
            k=sum(1 for x in st if x<o); sign*=(-1)**k; st.insert(k,o)
    return sign,tuple(st)
H2=np.zeros((n,n));H1=np.zeros((n,n));S2=np.zeros((n,n))
for j,d in enumerate(dets):
    for p in idx:
        for q in idx:
            if orbs[p][1]!=orbs[q][1]: continue
            v=cf(orbs[p][0],orbs[q][0])
            if v==0: continue
            r=app(d,[('c',p),('a',q)])
            if r: H1[pos[r[1]],j]+=r[0]*v
    for p,q in itertools.combinations(idx,2):
      for r_,s in itertools.combinations(idx,2):
        v=V2(orbs[p],orbs[q],orbs[r_],orbs[s])-V2(orbs[p],orbs[q],orbs[s],orbs[r_])
        if v==0: continue
        r=app(d,[('c',p),('c',q),('a',s),('a',r_)])
        if r: H2[pos[r[1]],j]+=r[0]*v
    S2[j,j]+=0.75
    for m in ms:
        up=orbs.index((m,1)); dn=orbs.index((m,-1))
        for m2 in ms:
            up2=orbs.index((m2,1)); dn2=orbs.index((m2,-1))
            r=app(d,[('c',dn2),('a',up2),('c',up),('a',dn)])
            if r: S2[pos[r[1]],j]+=r[0]
print("herm",abs(H2-H2.T).max(),abs(H1-H1.T).max())
ML=np.array([sum(orbs[i][0] for i in d) for d in dets])
phase=np.exp(1j*np.pi/2*ML)
def levels(dqB):
    H=H2+H1*(dqB+1e-5)*B
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<n:
        j=i
        while j<n and w[j]-w[i]<1e-3: j+=1
        vs=v[:,i:j]; dim=j-i
        s2=np.trace(vs.T@S2@vs)/dim; S=(-1+np.sqrt(1+4*s2))/2
        chi=np.real(np.sum(np.abs(vs)**2*phase[:,None]))
        lab={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}[(dim,int(round(chi)))]
        out.append((w[i],f"{int(round(2*S+1))}{lab}g")); i=j
    return out
import json
L=levels(0); print("free ion",[(t,round((e-L[0][0])/B,3)) for e,t in L[:12]])
res=[]
for dq in np.arange(0,4.01,0.5):
    L=levels(dq); e0=L[0][0]
    res.append({"dq_over_b":float(dq),"levels":[{"term":t,"e_over_b":round((e-e0)/B,3)} for e,t in L[:6]]})
    print(dq,[(t,round((e-e0)/B,3)) for e,t in L[:7]])
json.dump(res,open('res.json','w'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,161); Y=[]
for x in xs:
    L=levels(x); Y.append([(e-L[0][0])/B for e,t in L])
m=min(len(y) for y in Y); Y=np.array([y[:m] for y in Y])
plt.figure(figsize=(7,8)); plt.plot(xs,Y,'k.',ms=1); plt.ylim(0,80); plt.xlabel('Dq/B'); plt.ylabel('E/B')
plt.title('Tanabe-Sugano d5 Oh, C/B=%.3f'%(C/B)); plt.savefig('diagram.png',dpi=120)
EOF
MPLCONFIGDIR=<SANDBOX_TMP>/mpl python3 ts.py; sha256sum diagram.png