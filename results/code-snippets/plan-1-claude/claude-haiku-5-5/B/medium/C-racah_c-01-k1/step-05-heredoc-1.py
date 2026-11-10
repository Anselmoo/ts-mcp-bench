import numpy as np, itertools
from scipy.special import sph_harm
ms=[-2,-1,0,1,2]
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m,th,ph): return sph_harm(m,l,ph,th)
D=[Y(2,m,TH,PH) for m in ms]
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
Vang=X**4+Yc**4+Z**4-0.6
M=np.zeros((5,5),complex)
for a in range(5):
    for b in range(5):
        M[a,b]=np.sum(W*np.conj(D[a])*Vang*D[b])
ev=np.linalg.eigvalsh(M)
print("ligand eig raw",ev)
et,ee=ev[:3].mean(),ev[3:].mean()
h1=M/(ee-et)*10.0
print("h1 eig", np.linalg.eigvalsh(h1))
ANG={}
for k in [2,4]:
    G=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q,TH,PH)
        A=np.array([[np.sum(W*np.conj(D[a])*D[c]*np.conj(Ykq)) for c in range(5)] for a in range(5)])
        Bm=np.array([[np.sum(W*np.conj(D[b])*D[d]*Ykq) for d in range(5)] for b in range(5)])
        G+=np.einsum('ac,bd->acbd',A,Bm)
    ANG[k]=G*4*np.pi/(2*k+1)
states=list(itertools.combinations(range(10),3))
idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,st):
    occ=list(st); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(sorted(occ))
TWO=[]
for a in range(10):
  for b in range(10):
    for c in range(10):
      for d in range(10):
        if a==b or c==d: continue
        oa,sa=divmod(a,2); ob,sb=divmod(b,2); oc,sc=divmod(c,2); od,sd=divmod(d,2)
        if sa!=sc or sb!=sd: continue
        TWO.append((a,b,c,d,oa,oc,ob,od))
n=len(states)
P1=np.zeros((n,n),complex); P2={2:np.zeros((n,n),complex),4:np.zeros((n,n),complex)}
for j,st in enumerate(states):
    for a in range(5):
        for b in range(5):
            if abs(h1[a,b])<1e-14: continue
            for s in range(2):
                r=apply_ops([('c',2*a+s),('a',2*b+s)],st)
                if r is None: continue
                sg,ns=r; P1[idx[ns],j]+=sg*h1[a,b]
    for (a,b,c,d,oa,oc,ob,od) in TWO:
        for k in (2,4):
            v=ANG[k][oa,oc,ob,od]
            if abs(v)<1e-14: continue
            r=apply_ops([('c',a),('c',b),('a',d),('a',c)],st)
            if r is None: continue
            sg,ns=r; P2[k][idx[ns],j]+=0.5*sg*v
print("imag", np.abs(P1.imag).max(), np.abs(P2[2].imag).max(), np.abs(P2[4].imag).max())
def energies(Dq,B,C):
    F4=63*C/5.0; F2=49*B+5*F4/9.0
    H=np.real(Dq*P1+F2*P2[2]+F4*P2[4])
    ms3=[i for i,s in enumerate(states) if all(x%2==0 for x in s)]
    quart=np.sort(np.linalg.eigvalsh(H[np.ix_(ms3,ms3)]))
    ms1=[i for i,s in enumerate(states) if (sum(1 for x in s if x%2==0)-sum(1 for x in s if x%2==1))==1]
    all1=list(np.sort(np.linalg.eigvalsh(H[np.ix_(ms1,ms1)])))
    for qe in quart:
        k=int(np.argmin([abs(x-qe) for x in all1])); all1.pop(k)
    return quart, np.array(all1)
q,d=energies(1000.0,500.0,2000.0)
print("quartets",q)
print("doublets",d)
