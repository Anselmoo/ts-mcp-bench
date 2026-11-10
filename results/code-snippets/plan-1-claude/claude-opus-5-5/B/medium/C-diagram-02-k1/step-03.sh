cat > ts.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B,C=814.,3902.
F={2:49*B+7*C,4:441*C/35}
ms=[-2,-1,0,1,2]
def ck(k,m,mp): return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
so=[(m,s) for s in (0,1) for m in ms]; n=10
ckt={(k,m,mp):ck(k,m,mp) for k in (2,4) for m in ms for mp in ms}
def g(a,b,c,d):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(ckt[k,ma,mc]*ckt[k,md,mb]*F[k] for k in (2,4))
G=np.zeros((n,)*4)
for idx in itertools.product(range(n),repeat=4): G[idx]=g(*idx)
dets=list(itertools.combinations(range(n),4)); N=len(dets); ix={d:i for i,d in enumerate(dets)}
def apply(ops,det):
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
nz=[(i,j,k,l,G[i,j,k,l]) for i,j,k,l in itertools.product(range(n),repeat=4) if abs(G[i,j,k,l])>1e-12]
HC=np.zeros((N,N))
for jd,d in enumerate(dets):
    for i_,jj,k,l,v in nz:
        nd,s=apply([(i_,1),(jj,1),(l,0),(k,0)],d)
        if nd: HC[ix[nd],jd]+=0.5*v*s
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
print("sym",abs(HC-HC.T).max(),abs(V-V.T).max())
Sz=np.diag([sum(0.5 if so[o][1] else -0.5 for o in d) for d in dets])
Sp=np.zeros((N,N))
for j,d in enumerate(dets):
    for m in ms:
        nd,s=apply([(so.index((m,1)),1),(so.index((m,0)),0)],d)
        if nd: Sp[ix[nd],j]+=s
S2=Sp.T@Sp+Sz@Sz-Sz
C4=np.diag([np.exp(1j*np.pi/2*sum(so[o][0] for o in d)) for d in dets])
def levels(dqb):
    eps=1e-6 if dqb==0 else 0
    w,U=np.linalg.eigh(HC/B+(dqb+eps)*V)
    w0=np.linalg.eigvalsh(HC/B+dqb*V)
    out=[];i=0
    while i<N:
        j=i
        while j<N and w[j]-w[i]<1e-8: j+=1
        Us=U[:,i:j]; dim=j-i
        Sv=np.trace(Us.T@S2@Us)/dim; S=(-1+np.sqrt(1+4*Sv))/2
        mult=int(round(2*S+1)); orb=int(round(dim/mult))
        P=Us@Us.T; msk=np.isclose(np.diag(Sz),S)
        chi=np.real(np.trace((P@C4)[np.ix_(msk,msk)]))
        lab={1:'A1' if chi>0 else 'A2',2:'E',3:'T1' if chi>0 else 'T2'}.get(orb,'?%d'%dim)
        out.append((f"{mult}{lab}g",w0[i:j].mean())); i=j
    return out
for k in range(9):
    dq=0.5*k; L=levels(dq); e0=L[0][1]
    print(dq,[(t,round(e-e0,4)) for t,e in L[:8]])
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,161); ys=np.array([ (lambda w:w-w[0])(np.linalg.eigvalsh(HC/B+x*V)) for x in xs])
plt.figure(figsize=(6,8)); plt.plot(xs,ys,'k',lw=0.5); plt.ylim(0,80)
plt.xlabel('Dq/B'); plt.ylabel('E/B'); plt.title('Tanabe-Sugano d4 Oh, B=814, C=3902 cm-1'); plt.savefig('diagram.png',dpi=120)
EOF
python3 ts.py; sha256sum diagram.png; realpath diagram.png