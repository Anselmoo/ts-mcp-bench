mkdir -p <SANDBOX_TMP>/me7 && cd <SANDBOX_TMP>/me7 && cat > ts.py <<'EOF'
import numpy as np, itertools, json
from sympy.physics.wigner import wigner_3j
B,C=551.,2511.
F4=C/35; F2=B+5*F4
Fk={0:0.0,2:F2*49,4:F4*441}
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
orbs=[(m,s) for s in (0,1) for m in ms]; n=10
G=np.zeros((n,)*4)
for a,b,c,d in itertools.product(range(n),repeat=4):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    G[a,b,c,d]=sum(ck(k,ma,mc)*ck(k,md,mb)*Fk[k] for k in (0,2,4))
dets=list(itertools.combinations(range(n),6)); index={d:i for i,d in enumerate(dets)}; N=len(dets)
def apply_ops(ops,det):
    occ=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            occ=sorted(occ+[o]); sign*=(-1)**occ.index(o)
    return tuple(occ),sign
def onebody(h):
    M=np.zeros((N,N))
    for j,d in enumerate(dets):
        for p in range(n):
            for q in range(n):
                if h[p,q]==0: continue
                r,s=apply_ops([('c',p),('a',q)],d)
                if r: M[index[r],j]+=h[p,q]*s
    return M
HC=np.zeros((N,N))
nz=[idx for idx in itertools.product(range(n),repeat=4) if G[idx]!=0]
for j,d in enumerate(dets):
    for p,q,r,s_ in nz:
        if r not in d or s_ not in d: continue
        res,sg=apply_ops([('c',p),('c',q),('a',s_),('a',r)],d)
        if res: HC[index[res],j]+=0.5*G[p,q,r,s_]*sg
v=np.zeros((5,5))
for i,m in enumerate(ms): v[i,i]={0:6,1:-4,2:1}[abs(m)]
v[0,4]=v[4,0]=5
HCF=onebody(np.kron(np.eye(2),v))
sp=np.zeros((n,n)); sz=np.zeros((n,n))
for i,(m,s) in enumerate(orbs):
    sz[i,i]=0.5 if s==0 else -0.5
    if s==1: sp[orbs.index((m,0)),i]=1
Sp=onebody(sp); Sz=onebody(sz); S2=Sp.T@Sp+Sz@Sz+Sz
Mz=np.array([sum(orbs[o][0] for o in d) for d in dets])
sel=np.where(abs(np.diag(Sz))<1e-9)[0]
H0=HC[np.ix_(sel,sel)]; H1=HCF[np.ix_(sel,sel)]; S2s=S2[np.ix_(sel,sel)]
C4=np.exp(-1j*np.pi/2*Mz[sel])
print('sym',np.abs(HC-HC.T).max())
def levels(dq,labdq=None):
    Dq=dq*B
    H=H0+Dq*H1
    w,U=np.linalg.eigh(H+1e-3*S2s)
    E=np.diag(U.T@H@U).real; S2v=np.diag(U.T@S2s@U)
    # labels from perturbed Dq if needed
    out=[]
    Hl=H0+(labdq if labdq is not None else Dq)*H1
    wl,Ul=np.linalg.eigh(Hl+1e-3*S2s)
    # cluster on wl
    i=0; res=[]
    while i<len(wl):
        j=i
        while j+1<len(wl) and wl[j+1]-wl[i]<1e-4: j+=1
        idx=range(i,j+1); d=j-i+1
        Uc=Ul[:,i:j+1]
        S2val=np.mean(np.diag(Uc.T@S2s@Uc)); S=(-1+np.sqrt(1+4*S2val))/2
        tr=np.trace(Uc.conj().T@(C4[:,None]*Uc)).real
        lab={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}.get((d,round(tr)),f'?{d},{tr:.2f}')
        Eex=np.mean(np.diag(Uc.T@(H0+Dq*H1)@Uc))
        res.append((Eex,f'{int(round(2*S+1))}{lab}g'))
        i=j+1
    res.sort()
    return res
pts=[];allres={}
for k in range(9):
    dq=0.5*k
    r=levels(dq, labdq=(1e-4*B if dq==0 else None))
    e0=r[0][0]
    lv=[dict(term=t,e_over_b=round((e-e0)/B,4)) for e,t in r[:6]]
    pts.append(dict(dq_over_b=dq,levels=lv)); print(dq,[(l['term'],l['e_over_b']) for l in lv])
json.dump(pts,open('pts.json','w'))
# plot
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,161); curves=[]
for x in xs:
    r=levels(x, labdq=(1e-4*B if x==0 else None)); e0=r[0][0]
    curves.append([(e-e0)/B for e,t in r])
m=min(len(c) for c in curves)
Y=np.array([c[:m] for c in curves])
plt.figure(figsize=(7,8)); plt.plot(xs,Y,'k-',lw=0.6); plt.ylim(0,80)
plt.xlabel('Dq/B'); plt.ylabel('E/B'); plt.title('Tanabe–Sugano d6 Oh, B=551, C=2511 cm$^{-1}$')
plt.savefig('/tmp/tsbench-run-gtlh1zga/diagram.png',dpi=120)
EOF
MPLCONFIGDIR=<SANDBOX_TMP>/me7 time python3 ts.py