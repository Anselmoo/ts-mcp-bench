import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
B=806.;C=3570.
F={0:0.,2:49*B+7*C,4:441*C/35}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # c^k(l m1, l m2) = <l m1|C^k_{m1-m2}|l m2>
    q=m1-m2
    if abs(q)>k: return 0.
    # c^k = (-1)^m1 (2l+1) (l k l;0 0 0)(l k l; -m1 q m2)
    from sympy.physics.wigner import wigner_3j
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
# spin-orbitals: (m, s) s=+1/-1
orbs=[(m,s) for m in ms for s in (1,-1)]
def V2(a,b,c,d): # <ab|1/r12|cd>
    if a[1]!=c[1] or b[1]!=d[1]: return 0.
    if a[0]+b[0]!=c[0]+d[0]: return 0.
    return sum(ck(k,a[0],c[0])*ck(k,d[0],b[0])*F[k] for k in (0,2,4))
def cf(m1,m2,Dq):
    if m1==m2: return {0:6,1:-4,-1:-4,2:1,-2:1}[m1]*Dq
    if abs(m1-m2)==4: return 5*Dq
    return 0.
idx=range(10)
dets=[d for d in itertools.combinations(idx,5) if sum(orbs[i][1] for i in d)==1]
n=len(dets); pos={d:i for i,d in enumerate(dets)}
def apply_ann_cre(det,ops):
    # ops list of (type,orb) applied right to left; returns sign,newdet or None
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
    # one-body
    for p in idx:
        for q in idx:
            if orbs[p][1]!=orbs[q][1]: continue
            v=cf(orbs[p][0],orbs[q][0],1.0)
            if v==0: continue
            r=apply_ann_cre(d,[('c',p),('a',q)])
            if r: H1[pos[r[1]],j]+=r[0]*v
    for p,q in itertools.combinations(idx,2):
      for r_,s in itertools.combinations(idx,2):
        # 1/2 sum pqrs <pq|rs> c+p c+q c s c r ; using p<q, r<s antisymmetrized
        v=V2(orbs[p],orbs[q],orbs[r_],orbs[s])-V2(orbs[p],orbs[q],orbs[s],orbs[r_])
        if v==0: continue
        r=apply_ann_cre(d,[('c',p),('c',q),('a',s),('a',r_)])
        if r: H2[pos[r[1]],j]+=r[0]*v
    # S^2 = S-S+ + Sz^2 + Sz
    sz=0.5
    S2[j,j]+=sz*sz+sz
    for m in ms:
        up=orbs.index((m,1)); dn=orbs.index((m,-1))
        for m2 in ms:
            up2=orbs.index((m2,1)); dn2=orbs.index((m2,-1))
            r=apply_ann_cre(d,[('c',dn2),('a',up2),('c',up),('a',dn)])
            if r: S2[pos[r[1]],j]+=r[0]
ML=np.array([sum(orbs[i][0] for i in d) for d in dets])
phase=np.exp(1j*np.pi/2*ML)
def levels(dqB):
    H=H2+H1*dqB*B+1e-6*B*H1
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
res=[];allL={}
for dq in np.arange(0,4.01,0.5):
    L=levels(dq); e0=L[0][0]
    res.append({"dq_over_b":float(dq),"levels":[{"term":t,"e_over_b":round((e-e0)/B,3)} for e,t in L[:6]]})
    print(dq,[(t,round((e-e0)/B,3)) for e,t in L[:8]])
json.dump(res,open('res.json','w'))
# plot
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,161); Y=[]
for x in xs:
    L=levels(x); Y.append([(e-L[0][0])/B for e,t in L])
m=min(len(y) for y in Y); Y=np.array([y[:m] for y in Y])
plt.figure(figsize=(7,8)); plt.plot(xs,Y,'k',lw=.7); plt.ylim(0,80); plt.xlabel('Dq/B'); plt.ylabel('E/B')
plt.title('d5 Oh, C/B=%.3f'%(C/B)); plt.savefig('/tmp/w/diagram.png',dpi=120)
