import numpy as np, itertools
from scipy.special import sph_harm
nt, nphi = 40, 80
xg, wg = np.polynomial.legendre.leggauss(nt)
th = np.arccos(xg); ph = np.arange(nphi)*2*np.pi/nphi; wph = 2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = (wg[:,None]*wph*np.ones_like(TH))
ms=[-2,-1,0,1,2]
def Y(l,m): return sph_harm(m,l,PH,TH)
def ang(k,ma,mc,mb,md):
    s=0
    for q in range(-k,k+1):
        A=np.sum(W*np.conj(Y(2,ma))*np.conj(Y(k,q))*Y(2,mc))
        B=np.sum(W*np.conj(Y(2,mb))*Y(k,q)*Y(2,md))
        s+=A*B
    return 4*np.pi/(2*k+1)*s
so=[(m,s) for m in ms for s in (0,1)]
N=len(so)
V={}
for k in (2,4):
    Vk=np.zeros((N,N,N,N),complex)
    for a,(ma,sa) in enumerate(so):
        for c,(mc,sc) in enumerate(so):
            if sa!=sc: continue
            for b,(mb,sb) in enumerate(so):
                for d,(md,sd) in enumerate(so):
                    if sb!=sd: continue
                    Vk[a,b,c,d]=ang(k,ma,mc,mb,md)
    V[k]=Vk
dets=list(itertools.combinations(range(N),4)); idx={d:i for i,d in enumerate(dets)}
def ann(st,x):
    if x not in st: return None,0
    p=st.index(x); return st[:p]+st[p+1:], (-1)**p
def cre(st,x):
    if x in st: return None,0
    p=sum(1 for y in st if y<x); return tuple(sorted(st+(x,))), (-1)**p
def ee_ops(F2,F4):
    Vt=F2*V[2]+F4*V[4]
    M=np.zeros((len(dets),len(dets)),complex)
    for j,dj in enumerate(dets):
        for c in range(N):
            for d in range(N):
                for b in range(N):
                    for a in range(N):
                        v=Vt[a,b,c,d]
                        if abs(v)<1e-12: continue
                        st,s1=ann(dj,c)
                        if st is None: continue
                        st,s2=ann(st,d)
                        if st is None: continue
                        st,s3=cre(st,b)
                        if st is None: continue
                        st,s4=cre(st,a)
                        if st is None: continue
                        M[idx[st],j]+=0.5*v*s1*s2*s3*s4
    return M
# one-electron: real d orbitals in complex basis
def cvec(l=2):
    c={}
    c['z2']={0:1}
    c['x2y2']={2:1/np.sqrt(2),-2:1/np.sqrt(2)}
    c['xy']={-2:1/np.sqrt(2)*(-1j)*-1 ,2:-1/np.sqrt(2)*(-1j)*-1}  # placeholder replaced below
    return c
def orbvecs():
    vec={}
    v=np.zeros(5,complex); v[2]=1; vec['z2']=v
    v=np.zeros(5,complex); v[0]=1/np.sqrt(2); v[4]=1/np.sqrt(2); vec['x2y2']=v
    v=np.zeros(5,complex); v[0]=-1j/np.sqrt(2); v[4]=1j/np.sqrt(2); vec['xy']=v
    v=np.zeros(5,complex); v[1]=-1/np.sqrt(2); v[3]=1/np.sqrt(2); vec['xz']=v
    v=np.zeros(5,complex); v[1]=-1j/np.sqrt(2); v[3]=-1j/np.sqrt(2); vec['yz']=v
    return vec
def cf_matrix(Dq):
    vec=orbvecs(); E={'z2':6*Dq,'x2y2':6*Dq,'xy':-4*Dq,'xz':-4*Dq,'yz':-4*Dq}
    h=np.zeros((5,5),complex)
    for k,v in vec.items():
        h+=E[k]*np.outer(v,v.conj())
    H=np.zeros((N,N),complex)
    for a,(ma,sa) in enumerate(so):
        for b,(mb,sb) in enumerate(so):
            if sa==sb: H[a,b]=h[ma+2,mb+2]
    return H
def oneel(H1):
    M=np.zeros((len(dets),len(dets)),complex)
    for j,dj in enumerate(dets):
        for b in range(N):
            for a in range(N):
                if abs(H1[a,b])<1e-14: continue
                st,s1=ann(dj,b)
                if st is None: continue
                st,s2=cre(st,a)
                if st is None: continue
                M[idx[st],j]+=H1[a,b]*s1*s2
    return M
