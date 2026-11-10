cat << 'EOF' | python3 - 2>&1 | tail -5
import numpy as np, itertools
from scipy.special import eval_legendre
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq
def dorb(th,ph):
    x=np.sin(th)*np.cos(ph); y=np.sin(th)*np.sin(ph); z=np.cos(th)
    s=1/np.sqrt(np.pi)
    return [s*np.sqrt(15)/2*x*y, s*np.sqrt(15)/2*y*z, s*np.sqrt(5)/4*(3*z*z-1), s*np.sqrt(15)/2*x*z, s*np.sqrt(15)/4*(x*x-y*y)]
nt,npz=20,40
xg,wg=leggauss(nt); th=np.arccos(xg); ph=np.arange(npz)*2*np.pi/npz; wph=2*np.pi/npz
pts=[]; W=[]
for i in range(nt):
    for j in range(npz):
        pts.append((th[i],ph[j])); W.append(wg[i]*wph)
W=np.array(W)
Y=np.array([dorb(t,p) for t,p in pts])
U=np.array([[np.sin(t)*np.cos(p),np.sin(t)*np.sin(p),np.cos(t)] for t,p in pts])
cosg=np.clip(U@U.T,-1,1)
Ks=[0,2,4]
T=np.einsum('i,ia,ic->iac',W,Y,Y)
A={k:np.einsum('iac,ij,jbd->abcd',T,eval_legendre(k,cosg),T) for k in Ks}
nso=10
basis=[sum(1<<i for i in occ) for occ in itertools.combinations(range(nso),7)]
idx={b:i for i,b in enumerate(basis)}
N=len(basis)
def par(st,i): return (-1)**bin(st & ((1<<i)-1)).count('1')
def build_2body(Gt):
    H=np.zeros((N,N))
    for j,b in enumerate(basis):
        for a_ in range(nso):
          for b_ in range(nso):
            for c in range(nso):
              for d in range(nso):
                g=Gt[a_,b_,c,d]
                if abs(g)<1e-12: continue
                st=b; sign=1
                if not (st>>c)&1: continue
                sign*=par(st,c); st^=(1<<c)
                if not (st>>d)&1: continue
                sign*=par(st,d); st^=(1<<d)
                if (st>>b_)&1: continue
                sign*=par(st,b_); st|=(1<<b_)
                if (st>>a_)&1: continue
                sign*=par(st,a_); st|=(1<<a_)
                H[idx[st],j]+=0.5*g*sign
    return H
def build_1body(h):
    H=np.zeros((N,N))
    for j,b in enumerate(basis):
        for p in range(nso):
            for q in range(nso):
                if abs(h[p,q])<1e-14: continue
                st=b
                if not (st>>q)&1: continue
                sign=par(st,q); st^=(1<<q)
                if (st>>p)&1: continue
                sign*=par(st,p); st|=(1<<p)
                H[idx[st],j]+=h[p,q]*sign
    return H
def gspin(k):
    G=np.zeros((nso,nso,nso,nso))
    for a in range(nso):
     for b in range(nso):
      for c in range(nso):
       for d in range(nso):
        if a%2==c%2 and b%2==d%2:
            G[a,b,c,d]=A[k][a//2,b//2,c//2,d//2]
    return G
G={k:gspin(k) for k in Ks}
Vang=U[:,0]**4+U[:,1]**4+U[:,2]**4-0.6
M=np.einsum('i,ia,ib->ab',W*Vang,Y,Y)
ev=np.linalg.eigvalsh(M)
et=ev[:3].mean(); ee=ev[3:].mean()
h0=M*10/(ee-et)
hs=np.zeros((nso,nso))
for a in range(nso):
  for b in range(nso):
    if a%2==b%2: hs[a,b]=h0[a//2,b//2]
H1=build_1body(hs)
Gop={k:build_2body(G[k]) for k in Ks}
nup=np.array([sum(1 for i in range(0,nso,2) if (b>>i)&1) for b in basis])
ids5=np.where(nup==5)[0]; ids4=np.where(nup==4)[0]
B,C=922.,4156.
F4=441*C/35; F2=(441*B+5*F4)/9
def states(Dq):
    H=Dq*H1+F2*Gop[2]+F4*Gop[4]
    q=np.linalg.eigvalsh(H[np.ix_(ids5,ids5)])
    d=list(np.linalg.eigvalsh(H[np.ix_(ids4,ids4)]))
    for x in q:
        k=int(np.argmin([abs(y-x) for y in d])); d.pop(k)
    return q[0], min(d)
for Dq in [0,500,1000,1500,1700,1800,2000,2500]:
    eq,ed=states(Dq); print(Dq, round(eq-ed,1))
x=brentq(lambda D: states(D)[0]-states(D)[1],0,5000,xtol=1e-6)
print("crossover Dq =",round(x,1), "Dq/B=",round(x/B,3))
EOF