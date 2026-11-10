import numpy as np
from scipy.sparse import csr_matrix, identity, kron
from numpy.polynomial.legendre import leggauss
from numpy.polynomial import legendre as L
from scipy.optimize import least_squares
nt, nphi = 16, 32
xg, wg = leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
pts=[];w=[]
for ct,wt in zip(xg,wg):
    st=np.sqrt(1-ct*ct)
    for ph in phis:
        pts.append([st*np.cos(ph), st*np.sin(ph), ct]); w.append(wt*2*np.pi/nphi)
P=np.array(pts); W=np.array(w)
x,y,z=P.T
funcs=[x*y, y*z, z*x, x*x-y*y, 2*z*z-x*x-y*y]
F=np.array([f/np.sqrt(np.sum(W*f*f)) for f in funcs])
cosg=np.clip(P@P.T,-1,1)
def Pk(k,c):
    co=np.zeros(k+1); co[k]=1; return L.legval(c,co)
G=np.einsum('ai,ci,i->aci',F,F,W)
Ak={k:np.einsum('aci,ij,bdj->acbd',G,Pk(k,cosg),G) for k in [2,4]}
M=10
I2=identity(2,format='csr'); Z=csr_matrix(np.diag([1.,-1.])); am=csr_matrix(np.array([[0,1.],[0,0]]))
def cop(i):
    mats=[Z if j<i else (am if j==i else I2) for j in range(M)]
    out=mats[0]
    for m in mats[1:]: out=kron(out,m,format='csr')
    return out
c=[cop(i) for i in range(M)]
cd=[m.T.tocsr() for m in c]
num=[cd[i]@c[i] for i in range(M)]
up=[2*o for o in range(5)]; dn=[2*o+1 for o in range(5)]
Nup=sum(num[i] for i in up).diagonal(); Ndn=sum(num[i] for i in dn).diagonal()
idx=np.where(np.isclose(Nup,5)&np.isclose(Ndn,3))[0]
# precompute operator pieces restricted to sector: one-body and two-body k=2,4 parts
def restrict(Mat): return Mat[idx][:,idx].toarray()
one={}
for o in range(5):
    for s in range(2):
        one[o]=one.get(o,0)+restrict(num[2*o+s])
Ops={2:0,4:0}
terms=[]
for a in range(5):
 for b in range(5):
  for cc in range(5):
   for d in range(5):
    for s in range(2):
     for t in range(2):
      i=2*a+s; j=2*b+t; k=2*cc+s; l=2*d+t
      terms.append((a,cc,b,d,restrict(0.5*cd[i]@cd[j]@c[l]@c[k])))
# accumulate
Hk={2:np.zeros((len(idx),)*2),4:np.zeros((len(idx),)*2)}
for (a,cc,b,d,op) in terms:
    for k in [2,4]:
        v=Ak[k][a,cc,b,d]
        if abs(v)>1e-10: Hk[k]+=v*op
t2=one[0]+one[1]+one[2]; eg=one[3]+one[4]
def H(B,C,Dq):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    return F2*Hk[2]+F4*Hk[4]+6*Dq*t2-4*Dq*eg
def levels(p):
    B,C,Dq=p
    return np.linalg.eigvalsh(H(B,C,Dq))
def distinct(ev,tol=1e-3):
    out=[]
    for e in ev:
        if not out or abs(e-out[-1][0])>tol: out.append([e,1])
        else: out[-1][1]+=1
    return out
ev=levels((1000,4000,0))
print(distinct(ev))
obs=np.array([3600.,7870.,16410.])
def resid(p,perm):
    ev=levels(p); d=distinct(ev)
    e0=d[0][0]
    ex=[dd[0]-e0 for dd in d[1:]]
    if len(ex)<3: return np.ones(3)*1e6
    pred=np.array([ex[i] for i in perm])
    return (pred-obs)/obs
import itertools
sols=[]
for perm in [(0,1,2)]:
  for g in [(800,3000,360),(700,4000,600),(900,3500,400),(600,3000,1000)]:
    r=least_squares(resid,g,args=(perm,),bounds=([100,500,-5000],[5000,10000,5000]))
    sols.append((r.cost,r.x))
for s in sols: print(s)
d=distinct(levels(sols[0][1]))
print([ (round(e-d[0][0],1),n) for e,n in d])
