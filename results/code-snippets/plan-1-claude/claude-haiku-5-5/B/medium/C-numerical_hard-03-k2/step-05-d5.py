import numpy as np, itertools
from scipy.special import sph_harm
nth,nph=24,48
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
X=np.sin(TH)*np.cos(PH); Y=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
def nrm(f): return f/np.sqrt(np.sum(f*f*W))
fs=[nrm(X*Y),nrm(Y*Z),nrm(X*Z),nrm(2*Z**2-X**2-Y**2),nrm(X**2-Y**2)]
cf=[-4,-4,-4,6,6]
spinorb=[(i,s) for i in range(5) for s in [0.5,-0.5]]
no=10
ks=[0,2,4]
Ysh={(k,q):sph_harm(q,k,PH,TH) for k in ks for q in range(-k,k+1)}
def Vang2(k,a,c,b,d):
    tot=0
    for q in range(-k,k+1):
        Yk=Ysh[(k,q)]
        tot+= np.sum(fs[a]*np.conj(Yk)*fs[c]*W)*np.sum(fs[b]*Yk*fs[d]*W)
    return 4*np.pi/(2*k+1)*tot
M={k:np.zeros((no,)*4) for k in ks}
for a,b,c,d in itertools.product(range(no),repeat=4):
    if spinorb[a][1]!=spinorb[c][1] or spinorb[b][1]!=spinorb[d][1]: continue
    for k in ks:
        M[k][a,b,c,d]=Vang2(k,spinorb[a][0],spinorb[c][0],spinorb[b][0],spinorb[d][0]).real
states=[s for s in range(1<<no) if bin(s).count('1')==5]
idx={s:i for i,s in enumerate(states)}
D=len(states)
def apply(ops,s):
    sign=1
    for t,i in ops:
        occ=(s>>i)&1
        if t=='a':
            if not occ: return None,0
        else:
            if occ: return None,0
        sign*=(-1)**bin(s&((1<<i)-1)).count('1')
        s^=(1<<i)
    return s,sign
def op2(Vt):
    H=np.zeros((D,D))
    for a,b,c,d in np.argwhere(np.abs(Vt)>1e-12):
        v=Vt[a,b,c,d]
        for j,s in enumerate(states):
            # a+_a a+_b a_d a_c : apply a_c, a_d, then a+_b, a+_a
            s2,sg=apply([('a',c),('a',d),('c',b),('c',a)],s)
            if s2 is None: continue
            H[idx[s2],j]+=0.5*v*sg
    return H
Hk={k:op2(M[k]) for k in ks}
Hcf=np.diag([sum(cf[spinorb[i][0]] for i in range(no) if (s>>i)&1) for s in states]).astype(float)
def opE(i,j):
    H=np.zeros((D,D))
    for jj,s in enumerate(states):
        s2,sg=apply([('a',j),('c',i)],s)
        if s2 is not None: H[idx[s2],jj]+=sg
    return H
Sp=np.zeros((D,D))
for i in range(no):
    for j in range(no):
        if spinorb[i][1]==0.5 and spinorb[j][1]==-0.5 and spinorb[i][0]==spinorb[j][0]:
            Sp+=opE(i,j)
Sm=Sp.T
Sz=np.diag([sum(0.5 if spinorb[i][1]>0 else -0.5 for i in range(no) if (s>>i)&1) for s in states])
S2=Sm@Sp+Sz@Sz+Sz
ev,vec=np.linalg.eigh(S2)
Q=vec[:,np.abs(ev-0.75)<1e-6]
print("doublet dim",Q.shape[1])
np.savez('mats.npz',Hcf=Q.T@Hcf@Q,H0=Q.T@Hk[0]@Q,H2=Q.T@Hk[2]@Q,H4=Q.T@Hk[4]@Q)
print("F-integrals ang check: ", M[2].max(), M[4].max())
