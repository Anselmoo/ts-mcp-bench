import numpy as np, itertools
from scipy.special import sph_harm_y
xg,wg = np.polynomial.legendre.leggauss(20)
nphi=40
phis = np.arange(nphi)*2*np.pi/nphi; wphi = 2*np.pi/nphi
TH=[];PH=[];W=[]
for x,w in zip(xg,wg):
    for p in phis:
        TH.append(np.arccos(x)); PH.append(p); W.append(w*wphi)
TH=np.array(TH);PH=np.array(PH);W=np.array(W)
ms=[-2,-1,0,1,2]
def Y(l,m): return sph_harm_y(l,m,TH,PH)
Y2={m:Y(2,m) for m in ms}
X=np.sin(TH)*np.cos(PH); Yy=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
f = X**4+Yy**4+Z**4-0.6
Mf=np.array([[np.sum(W*np.conj(Y2[a])*f*Y2[b]) for b in ms] for a in ms])
ev=np.linalg.eigvalsh(Mf)
lo,hi=ev[:3].mean(),ev[3:].mean()
Hcf=Mf*10/(hi-lo)
print("cf eig", np.round(np.linalg.eigvalsh(Hcf),4))
Ang={}
for k in (0,2,4):
    Yk={q:Y(k,q) for q in range(-k,k+1)}
    arr=np.zeros((5,5,5,5),complex)
    for i1,m1 in enumerate(ms):
        for i3,m3 in enumerate(ms):
            A={q:np.sum(W*np.conj(Y2[m1])*Y2[m3]*np.conj(Yk[q])) for q in Yk}
            for i2,m2 in enumerate(ms):
                for i4,m4 in enumerate(ms):
                    B={q:np.sum(W*np.conj(Y2[m2])*Y2[m4]*Yk[q]) for q in Yk}
                    arr[i1,i3,i2,i4]=4*np.pi/(2*k+1)*sum(A[q]*B[q] for q in Yk)
    Ang[k]=arr
N=10
def spin_orb_V(k):
    V=np.zeros((N,N,N,N),complex)
    for a in range(N):
        for b in range(N):
            for c in range(N):
                for d in range(N):
                    if a%2!=c%2 or b%2!=d%2: continue
                    V[a,b,c,d]=Ang[k][a//2,c//2,b//2,d//2]
    return V
Vfull={k:spin_orb_V(k) for k in (0,2,4)}
h=np.zeros((N,N),complex)
for a in range(N):
    for b in range(N):
        if a%2==b%2: h[a,b]=Hcf[a//2,b//2]
def occ_states(nel,sz2):
    res=[]
    for occ in itertools.combinations(range(N),nel):
        nu=sum(1 for o in occ if o%2==0); nd=nel-nu
        if nu-nd==sz2: res.append(occ)
    return res
def apply_ops(ops,state):
    st=list(state); sign=1
    for typ,idx in ops:
        if typ=='a':
            if idx not in st: return None
            p=st.index(idx); sign*=(-1)**p; st.pop(p)
        else:
            if idx in st: return None
            p=sum(1 for x in st if x<idx); sign*=(-1)**p; st.insert(p,idx)
    return sign,tuple(st)
def build(basis):
    idx={s:i for i,s in enumerate(basis)}
    n=len(basis)
    M_cf=np.zeros((n,n)); M={k:np.zeros((n,n)) for k in (0,2,4)}
    for j,s in enumerate(basis):
        for a in range(N):
            for b in range(N):
                if abs(h[a,b])<1e-14: continue
                r=apply_ops([('c',a),('a',b)],s)
                if r and r[1] in idx: M_cf[idx[r[1]],j]+=r[0]*h[a,b].real
        for a in range(N):
          for b in range(N):
            for c in range(N):
              for d in range(N):
                vs={k:Vfull[k][a,b,c,d].real for k in (0,2,4)}
                if all(abs(v)<1e-12 for v in vs.values()): continue
                r=apply_ops([('a',c),('a',d),('c',b),('c',a)],s)
                if r and r[1] in idx:
                    for k in vs: M[k][idx[r[1]],j]+=0.5*r[0]*vs[k]
    return M_cf, M
