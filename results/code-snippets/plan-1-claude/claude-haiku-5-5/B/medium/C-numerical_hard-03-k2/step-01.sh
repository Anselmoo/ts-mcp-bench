
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
# quadrature on sphere
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
X=np.sin(TH)*np.cos(PH); Y=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
def nrm(f): return f/np.sqrt(np.sum(f*f*W))
orb=[]  # (name, angular function, spin)
fs=[nrm(X*Y),nrm(Y*Z),nrm(X*Z),nrm(2*Z**2-X**2-Y**2),nrm(X**2-Y**2)]
cf=[-4,-4,-4,6,6]  # in units of Dq
spinorb=[]
for i,f in enumerate(fs):
    for s in [0.5,-0.5]:
        spinorb.append((i,s))
no=len(spinorb)
# Gaunt-type angular coefficients
def ang(k,a,c):
    tot=0
    for q in range(-k,k+1):
        Ykq=sph_harm(q,k,PH,TH)
        A=np.sum(fs[a]*np.conj(Ykq)*fs[c]*W)
        tot=tot+A
    return 4*np.pi/(2*k+1)*tot
def angq(k,a,c):
    # returns list over q of A_q(a,c)=∫ f_a Y*_kq f_c ; sum over q of A(a,c)*B(b,d)
    return [np.sum(fs[a]*np.conj(sph_harm(q,k,PH,TH))*fs[c]*W) for q in range(-k,k+1)]
def Vang(k,a,c,b,d):
    A=angq(k,a,c); B=angq(k,b,d)
    # sum_q A_q(a,c)*B_q(b,d) where B uses Y_kq (conj appears with -q symmetry); use sum_q conj(Ystar) pattern
    return 4*np.pi/(2*k+1)*sum(A[i]*np.conj(np.conj(B[i])) for i in range(len(A)))
# Note: 1/r12 = sum_k sum_q 4pi/(2k+1) Y*_kq(1) Y_kq(2)
# <ab|cd> = sum_q 4pi/(2k+1) <a|Y*_kq|c><b|Y_kq|d>
def Vang2(k,a,c,b,d):
    tot=0
    for q in range(-k,k+1):
        Yk=sph_harm(q,k,PH,TH)
        tot+= np.sum(fs[a]*np.conj(Yk)*fs[c]*W)*np.sum(fs[b]*Yk*fs[d]*W)
    return 4*np.pi/(2*k+1)*tot
ks=[0,2,4]
M={k:np.zeros((no,)*4) for k in ks}
for a,b,c,d in itertools.product(range(no),repeat=4):
    sa,sb,sc,sd=spinorb[a][1],spinorb[b][1],spinorb[c][1],spinorb[d][1]
    if sa!=sc or sb!=sd: continue
    for k in ks:
        M[k][a,b,c,d]=Vang2(k,spinorb[a][0],spinorb[c][0],spinorb[b][0],spinorb[d][0]).real
# determinant basis
states=[s for s in range(1<<no) if bin(s).count('1')==5]
idx={s:i for i,s in enumerate(states)}
def apply(ops,s):
    # ops list of (type,i) applied right-to-left: list given in order applied first->last
    sign=1
    for t,i in ops:
        occ=(s>>i)&1
        if t=='a':  # annihilate
            if not occ: return None,0
            sign*= (-1)**bin(s & ((1<<i)-1)).count('1')
            s^=(1<<i)
        else:
            if occ: return None,0
            sign*= (-1)**bin(s & ((1<<i)-1)).count('1')
            s|=(1<<i)
    return s,sign
D=len(states)
def op2(Vt):
    H=np.zeros((D,D))
    nz=np.argwhere(np.abs(Vt)>1e-12)
    for a,b,c,d in nz:
        v=Vt[a,b,c,d]
        for j,s in enumerate(states):
            # a^+_a a^+_b a_d a_c  (0.5 factor)
            s2,sg=apply([('a',c),('a',d),('c',b),('c',a)],s)
            if s2 is None: continue
            H[idx[s2],j]+=0.5*v*sg
    return H
Hk={k:op2(M[k]) for k in ks}
# cubic field one-body
Hcf=np.zeros((D,D))
for j,s in enumerate(states):
    for i in range(no):
        if (s>>i)&1:
            Hcf[j,j]+=cf[spinorb[i][0]]
# S^2
def opE(i,j):
    H=np.zeros((D,D))
    for jj,s in enumerate(states):
        s2,sg=apply([('a',j),('c',i)],s)
        if s2 is not None: H[idx[s2],jj]+=sg
    return H
Sp=sum(opE(i,j) for i in range(no) for j in range(no) if spinorb[i][1]==0.5 and spinorb[j][1]==-0.5 and spinorb[i][0]==spinorb[j][0])
Sm=Sp.T
Sz=np.diag([sum(0.5 if spinorb[i][1]>0 else -0.5 for i in range(no) if (s>>i)&1) for s in states])
S2=Sm@Sp+Sz@Sz+Sz
# doublet subspace
ev,vec=np.linalg.eigh(S2)
Q=vec[:,np.abs(ev-0.75)<1e-6]
print("doublet dim",Q.shape[1])
np.savez('/tmp/mats.npz',Hcf=Q.T@Hcf@Q,H0=Q.T@Hk[0]@Q,H2=Q.T@Hk[2]@Q,H4=Q.T@Hk[4]@Q)
EOF
python3 /tmp/d5.py
