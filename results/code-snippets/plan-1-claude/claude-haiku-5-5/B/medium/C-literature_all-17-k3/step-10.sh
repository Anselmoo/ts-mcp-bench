python3 - <<'EOF'
import numpy as np
from scipy.special import lpmv, factorial
xg,wg=np.polynomial.legendre.leggauss(30)
phis=np.linspace(0,2*np.pi,60,endpoint=False); wp=2*np.pi/60
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij'); W=(wg[:,None]*wp*np.ones_like(TH))
def Y(l,m,th,ph):
    am=abs(m); N=np.sqrt((2*l+1)/(4*np.pi)*factorial(l-am)/factorial(l+am))
    y=N*lpmv(am,l,np.cos(th))*np.exp(1j*am*ph)
    if m<0: y=(-1)**am*np.conj(y)
    return y
ms=[-2,-1,0,1,2]
Yd={m:Y(2,m,TH,PH) for m in ms}
Ang={}
for k in (2,4):
    for a in ms:
        for c in ms:
            for q in range(-k,k+1):
                Ang[(a,c,k,q)]=np.sum(W*np.conj(Yd[a])*Yd[c]*np.conj(Y(k,q,TH,PH)))
so=[(m,s) for m in ms for s in (0,1)]
states=[x for x in range(1024) if bin(x).count('1')==8]
idx={x:i for i,x in enumerate(states)}; D=len(states)
def op(ops):
    M=np.zeros((D,D))
    for x in states:
        y=x; s=1; ok=True
        for typ,i in reversed(ops):
            nb=bin(y&((1<<i)-1)).count('1')
            if typ=='c':
                if not (y>>i)&1: ok=False;break
                y^=(1<<i); s*=(-1)**nb
            else:
                if (y>>i)&1: ok=False;break
                y|=(1<<i); s*=(-1)**nb
        if ok and y in idx: M[idx[y],idx[x]]+=s
    return M
Sp=sum(op([('a',2*m),('c',2*m+1)]) for m in range(5))
Sz=sum(0.5*(op([('a',2*m),('c',2*m)])-op([('a',2*m+1),('c',2*m+1)])) for m in range(5))
S2=Sp.T@Sp+Sz@Sz+Sz
Mops=[]
for a in range(10):
 for b in range(10):
  for c in range(10):
   for d in range(10):
    ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
    if sa!=sc or sb!=sd or a==b or c==d: continue
    coef=[]
    for k in (2,4):
        s=sum(Ang[(ma,mc,k,q)]*Ang[(mb,md,k,-q)]*(-1)**q for q in range(-k,k+1))
        coef.append(4*np.pi/(2*k+1)*s)
    if max(abs(x) for x in coef)<1e-12: continue
    Mops.append((np.array(coef),op([('a',a),('a',b),('c',d),('c',c)])))
Hs=[sum(0.5*c[i]*M for c,M in Mops) for i in (0,1)]
P=np.eye(D)
for name,H0 in [('F2',Hs[0]),('F4',Hs[1])]:
    # matrix of H0 projected; compute eigen in triplet/singlet sectors
    H=H0
    wt=np.linalg.eigvalsh(H+1e6*(S2-2*np.eye(D))@(S2-2*np.eye(D)))
    ws=np.linalg.eigvalsh(H+1e6*S2@S2)
    wt=wt[wt<5e5]; ws=ws[ws<5e5]
    # trace-based: centroid-free differences
    print(name,'triplet',np.round(np.unique(np.round(wt,3)),3),'singlet',np.round(np.unique(np.round(ws,3)),3))
EOF