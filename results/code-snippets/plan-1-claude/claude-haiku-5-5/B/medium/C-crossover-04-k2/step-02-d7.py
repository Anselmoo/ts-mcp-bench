import numpy as np, itertools
from scipy.special import eval_legendre
from numpy.polynomial.legendre import leggauss
def dorb(th,ph):
    x=np.sin(th)*np.cos(ph); y=np.sin(th)*np.sin(ph); z=np.cos(th)
    return [np.sqrt(15)/2*x*y, np.sqrt(15)/2*y*z, np.sqrt(5)/4*(3*z*z-1), np.sqrt(15)/2*x*z, np.sqrt(15)/4*(x*x-y*y)]
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
A={}
T=np.einsum('i,ia,ic->iac',W,Y,Y)
for k in Ks:
    Pk=eval_legendre(k,cosg)
    A[k]=np.einsum('iac,ij,jbd->abcd',T,Pk,T)
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
# spin-orbital two-body tensors
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
# one-electron octahedral potential
Vang=U[:,0]**4+U[:,1]**4+U[:,2]**4-0.6
M=np.einsum('i,ia,ib->ab',W*Vang,Y,Y)
ev=np.linalg.eigvalsh(M); print("M eig",ev)
# spin-orbital h: Dq * h0 where h0 has t2g=-4, eg=+6
ev_sorted=ev
# identify: t2g triplet = eigenvalues lowest-ratio; ratio ee/et should be -3/2
et=ev[:3].mean(); ee=ev[3:].mean()
print("ratio",ee/et)
# normalized: h0 = M * (10/(ee-et)) gives t2g -4 and eg +6 if ratio -3/2
s=10/(ee-et)
h0=M*s  # Dq=1 units with eigen
print("check", np.linalg.eigvalsh(h0))
# spin-orbital
def spin_h(h):
    H=np.zeros((nso,nso))
    for a in range(nso):
        for b in range(nso):
            if a%2==b%2: H[a,b]=h[a//2,b//2]
    return H
np.savez('ops.npz', **{f'G{k}':G[k] for k in Ks}, h0=spin_h(h0), M=M)
