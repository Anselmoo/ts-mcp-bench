import numpy as np, itertools, hashlib
from sympy.physics.wigner import wigner_3j
B,C=814.,3902.
F={0:0.0,2:49*B+7*C,4:441*C/35}
ms=[-2,-1,0,1,2]
def ck(k,m,mp): return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
so=[(m,s) for s in (0,1) for m in ms]; n=10
def g(a,b,c,d):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(ck(k,ma,mc)*ck(k,md,mb)*F[k] for k in (2,4))
G=np.zeros((n,)*4)
for idx in itertools.product(range(n),repeat=4): G[idx]=g(*idx)
dets=[c for c in itertools.combinations(range(n),4)]; N=len(dets); ix={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    # ops list of (idx,create?) applied right to left
    occ=list(det); sign=1
    for o,cr in reversed(ops):
        if cr:
            if o in occ: return None,0
            p=sum(1 for x in occ if x<o); occ.insert(p,o)
        else:
            if o not in occ: return None,0
            p=occ.index(o); occ.pop(p)
        sign*=(-1)**p
    return tuple(occ),sign
HC=np.zeros((N,N))
for j,d in enumerate(dets):
    for i_,jj in itertools.product(range(n),repeat=2):
        for k,l in itertools.product(range(n),repeat=2):
            v=G[i_,jj,k,l]
            if abs(v)<1e-12: continue
            nd,s=apply([(i_,1),(jj,1),(l,0),(k,0)],d)
            if nd: HC[ix[nd],j]+=0.5*v*s
h=np.zeros((n,n))
for a,(m,s) in enumerate(so):
    for b,(mp,sp) in enumerate(so):
        if s!=sp: continue
        if m==mp: h[a,b]={2:1,1:-4,0:6}[abs(m)]
        elif m==-mp and abs(m)==2: h[a,b]=5
V=np.zeros((N,N))
for j,d in enumerate(dets):
    for a in range(n):
        for b in range(n):
            if h[a,b]==0: continue
            nd,s=apply([(a,1),(b,0)],d)
            if nd: V[ix[nd],j]+=h[a,b]*s
# S^2 and C4
Sz=np.diag([sum(0.5 if so[o][1] else -0.5 for o in d) for d in dets])
Sp=np.zeros((N,N))
for j,d in enumerate(dets):
    for m in ms:
        a=so.index((m,1)); b=so.index((m,0))
        nd,s=apply([(a,1),(b,0)],d)
        if nd: Sp[ix[nd],j]+=s
S2=Sp.T@Sp+Sz@Sz+Sz
C4=np.diag([np.exp(1j*np.pi/2*sum(so[o][0] for o in d)) for d in dets])
def levels(dqb):
    eps=1e-6 if dqb==0 else 0
    H=HC/B+(dqb+eps)*V
    w,U=np.linalg.eigh(H)
    out=[];i=0
    while i<N:
        j=i
        while j<N and w[j]-w[i]<1e-7: j+=1
        Usub=U[:,i:j]; dim=j-i
        Sval=np.real(np.trace(Usub.T@S2@Usub))/dim; S=(-1+np.sqrt(1+4*Sval))/2
        mult=int(round(2*S+1)); orb=dim/mult
        # restrict to Ms=S
        P=Usub@Usub.T; msk=np.isclose(np.diag(Sz),S)
        chi=np.real(np.trace((P@C4)[np.ix_(msk,msk)]))
        orb=int(round(orb))
        lab={1:'A1' if chi>0 else 'A2',2:'E',3:'T1' if chi>0 else 'T2'}.get(orb,'?%d'%orb)
        out.append((f"{mult}{lab}g",np.mean(w[i:j]))); i=j
    if eps:
        w0=np.linalg.eigvalsh(HC/B); 
        # energies at exactly 0: cluster means approx; recompute by eps->0 extrapolation
        H2=HC/B+2*eps*V; w2=np.linalg.eigvalsh(H2)
    return out
res=[]
for k in range(9):
    dq=0.5*k; L=levels(dq); e0=L[0][1]
    res.append((dq,[(t,round(e-e0,3)) for t,e in L[:6]]))
    print(dq,res[-1][1])
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,161); ys=[]
for x in xs:
    w=np.linalg.eigvalsh(HC/B+x*V); ys.append(w-w[0])
ys=np.array(ys); plt.figure(figsize=(6,8)); plt.plot(xs,ys,'k',lw=0.5); plt.ylim(0,80)
plt.xlabel('Dq/B'); plt.ylabel('E/B'); plt.title('d4 Oh, C/B=%.3f'%(C/B)); plt.savefig('/tmp/w/diagram.png',dpi=120)
