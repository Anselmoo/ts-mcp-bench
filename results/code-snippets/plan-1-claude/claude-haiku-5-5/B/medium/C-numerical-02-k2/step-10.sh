python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
nt, nphi = 60, 120
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
TH = np.arccos(xg)[:,None]*np.ones((1,nphi)); PH = np.ones((nt,1))*phis[None,:]
W = (wg[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Y(l,m): return sph_harm_y(l,m,TH,PH)
ms=list(range(-2,3))
nvec=np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)],-1)
Rs=[(2,0,0),(-2,0,0),(0,2,0),(0,-2,0),(0,0,2),(0,0,-2)]
Vang=np.zeros(TH.shape)
for R in Rs:
    d=np.sqrt(((nvec-np.array(R))**2).sum(-1)); Vang+=1.0/d
Mlf=np.zeros((5,5),complex)
for i,m in enumerate(ms):
    for j,mp in enumerate(ms):
        Mlf[i,j]=np.sum(W*np.conj(Y(2,m))*Vang*Y(2,mp))
ev=np.linalg.eigvalsh(Mlf); t2=ev[:3].mean(); eg=ev[3:].mean()
h1=((Mlf-t2*np.eye(5))/(eg-t2)).real
def Ak(k,ma,mb,mc,md):
    tot=0
    for q in range(-k,k+1):
        Ykq=Y(k,q)
        I1=np.sum(W*np.conj(Y(2,ma))*np.conj(Ykq)*Y(2,mc))
        I2=np.sum(W*np.conj(Y(2,mb))*Ykq*Y(2,md))
        tot+=I1*I2
    return 4*np.pi/(2*k+1)*tot
A={}
for k in (2,4):
    T=np.zeros((5,5,5,5),complex)
    for a,b,c,d in itertools.product(range(5),repeat=4):
        T[a,b,c,d]=Ak(k,ms[a],ms[b],ms[c],ms[d])
    A[k]=T.real
N=10
def apply_ops(state, ops):
    st=list(state); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in st: return None,0
            p=st.index(i); sign*=(-1)**p; st.pop(p)
        else:
            if i in st: return None,0
            p=sum(1 for x in st if x<i); sign*=(-1)**p; st.insert(p,i)
    return tuple(st),sign
def build_dets(nel,Ms2):
    dets=[]
    for c in itertools.combinations(range(N),nel):
        nup=sum(1 for x in c if x<5); ndn=nel-nup
        if nup-ndn==Ms2: dets.append(c)
    return dets
def Hmat(D10,F2,F4,nel=7,Ms2=3):
    dets=build_dets(nel,Ms2); idx={d:i for i,d in enumerate(dets)}
    n=len(dets); H=np.zeros((n,n))
    ha=D10*h1
    for j,d in enumerate(dets):
        for a in range(5):
            for b in range(5):
                for s in (0,1):
                    new,sg=apply_ops(d,[('c',a+5*s),('a',b+5*s)])
                    if new is None: continue
                    H[idx[new],j]+=sg*ha[a,b]
        for a,b,c,dd in itertools.product(range(5),repeat=4):
            Vabcd=F2*A[2][a,b,c,dd]+F4*A[4][a,b,c,dd]
            if abs(Vabcd)<1e-12: continue
            for s1 in (0,1):
                for s2 in (0,1):
                    new,sg=apply_ops(d,[('c',a+5*s1),('c',b+5*s2),('a',dd+5*s2),('a',c+5*s1)])
                    if new is None: continue
                    H[idx[new],j]+=0.5*sg*Vabcd
    return H,dets
H,dets=Hmat(1.0,0.0,0.0); print("ndet",len(dets)); print("LF only:",np.round(np.linalg.eigvalsh(H),4))
EOF