import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares, brentq
ms=[-2,-1,0,1,2]
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*np.pi/nphi)
Y=lambda l,m,th,ph: sph_harm_y(l,m,th,ph)
D=[Y(2,m,TH,PH) for m in ms]
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
Vang=X**4+Yc**4+Z**4-0.6
M=np.array([[np.sum(W*np.conj(D[a])*Vang*D[b]) for b in range(5)] for a in range(5)])
ev=np.linalg.eigvalsh(M)
h1=M/(ev[3]-ev[0])*10.0
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
ms3=[i for i,s in enumerate(states) if all(x%2==0 for x in s)]
ms1=[i for i,s in enumerate(states) if (sum(1 for x in s if x%2==0)-sum(1 for x in s if x%2==1))==1]
def levels(Dq,B,C):
    F4=63*C/5.0; F2=49*B+5*F4/9.0
    H=np.real(Dq*P1+F2*P2[2]+F4*P2[4])
    q=np.sort(np.linalg.eigvalsh(H[np.ix_(ms3,ms3)]))
    a1=list(np.sort(np.linalg.eigvalsh(H[np.ix_(ms1,ms1)])))
    for qe in q:
        k=int(np.argmin([abs(x-qe) for x in a1])); a1.pop(k)
    return q-q[0], np.array(a1)-q[0]
# quartet check
q,d=levels(1417,122,500)
print("quartets rel:",np.round(q[[0,1,3,6,9]],1))
# Fit: unknowns Dq,B,C. Data: 4T2=14170, 4T1F=21710, 4T1P=33970, doublet=18540 (try each lowest doublet index)
obs_q=[14170,21710,33970]
def resid(p, dbl_idx):
    Dq,B,C=p
    q,d=levels(Dq,B,C)
    qs=[q[1],q[3],q[6]] # 4T2 (3 states idx1-3), 4T1F idx 4-6?, 4T1P idx 7-9
    return None
# Identify quartet multiplets from sorted list: [0]=A2, [1..3]=T2, [4..6]=T1F, [7..9]=T1P
def resid(p, di):
    Dq,B,C=p
    q,d=levels(Dq,B,C)
    model=[q[1],q[4],q[7],d[di]]
    return np.array(model)-np.array([14170,21710,33970,18540])
for di in range(0,6):
    best=None
    for g in [(1417,122,500),(1400,100,400),(1500,200,800),(1300,150,600)]:
        r=least_squares(resid,g,args=(di,),bounds=([500,0,0],[3000,1000,5000]))
        if best is None or r.cost<best.cost: best=r
    print("doublet idx",di,"energy",np.round(levels(*best.x)[1][di],1),"params",np.round(best.x,1),"resid",np.round(best.fun,1))
