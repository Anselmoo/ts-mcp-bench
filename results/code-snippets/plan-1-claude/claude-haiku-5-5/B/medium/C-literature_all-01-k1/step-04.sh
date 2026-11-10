
D=/tmp/tsbench-run-de_x16pn
cat << 'EOF' > $D/ni.py
import numpy as np, itertools, pickle
from scipy.special import sph_harm
ms=[-2,-1,0,1,2]
xg,wg=np.polynomial.legendre.leggauss(20)
nphi=40
th=np.arccos(xg); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(wg,np.ones(nphi))*2*np.pi/nphi
def Ykq(k,q,t,p): return sph_harm(q,k,p,t)
Yd={m:Ykq(2,m,TH,PH) for m in ms}
ang={}
for k in [0,2,4]:
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Yk=Ykq(k,q,TH,PH)
        X=np.zeros((5,5),complex); Z=np.zeros((5,5),complex)
        for i,a in enumerate(ms):
            for j,c in enumerate(ms):
                X[i,j]=np.sum(W*np.conj(Yd[a])*np.conj(Yk)*Yd[c])
                Z[i,j]=np.sum(W*np.conj(Yd[a])*Yk*Yd[c])
        # <b|Yk q|d> = Z[b,d]
        A+=np.einsum('ac,bd->abcd',X,Z)
    ang[k]=A*4*np.pi/(2*k+1)
so=[(m,s) for m in ms for s in (1,-1)]
N=len(so)
states=list(itertools.combinations(range(N),8))
idx={s:i for i,s in enumerate(states)}
def apply_c(st,i):
    if i not in st: return None,0
    pos=st.index(i)
    return tuple(x for x in st if x!=i),(-1)**pos
def apply_cdag(st,i):
    if i in st: return None,0
    pos=sum(1 for x in st if x<i)
    return tuple(sorted(st+(i,))),(-1)**pos
def twobody(k):
    H=np.zeros((len(states),len(states)),complex)
    A=ang[k]
    for si,st in enumerate(states):
        for c_ in range(N):
            for d_ in range(N):
                s1,g1=apply_c(st,d_)
                if s1 is None: continue
                s2,g2=apply_c(s1,c_)
                if s2 is None: continue
                for a_ in range(N):
                    for b_ in range(N):
                        ma,sa=so[a_]; mb,sb=so[b_]; mc,sc=so[c_]; md,sd=so[d_]
                        val=0
                        if sa==sc and sb==sd:
                            val+=A[ms.index(ma),ms.index(mb),ms.index(mc),ms.index(md)]
                        if sa==sd and sb==sc:
                            val-=A[ms.index(ma),ms.index(mb),ms.index(md),ms.index(mc)]
                        if abs(val)<1e-12: continue
                        s3,g3=apply_cdag(s2,b_)
                        if s3 is None: continue
                        s4,g4=apply_cdag(s3,a_)
                        if s4 is None: continue
                        H[idx[s4],si]+=0.5*val*g1*g2*g3*g4
    return H
Hk={k:twobody(k) for k in [2,4]}
r2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[ms.index(m)]=c
    return v
dz2=vec({0:1}); dx2y2=vec({2:1/r2,-2:1/r2})
dxy=vec({2:-1j/r2,-2:1j/r2}); dxz=vec({1:-1/r2,-1:1/r2}); dyz=vec({1:-1j/r2,-1:-1j/r2})
h1=np.zeros((5,5),complex)
for v in [dz2,dx2y2]: h1+=-6*np.outer(v,v.conj())
for v in [dxz,dyz,dxy]: h1+=4*np.outer(v,v.conj())
def onebody(h):
    H=np.zeros((len(states),len(states)),complex)
    for si,st in enumerate(states):
        for a_ in range(N):
            for c_ in range(N):
                ma,sa=so[a_]; mc,sc=so[c_]
                if sa!=sc: continue
                val=h[ms.index(ma),ms.index(mc)]
                if abs(val)<1e-12: continue
                s1,g1=apply_c(st,c_)
                if s1 is None: continue
                s2,g2=apply_cdag(s1,a_)
                if s2 is None: continue
                H[idx[s2],si]+=val*g1*g2
    return H
H1=onebody(h1)
def Splus():
    M=np.zeros((len(states),len(states)),complex)
    for si,st in enumerate(states):
        for m in ms:
            a=so.index((m,1)); b=so.index((m,-1))
            s1,g1=apply_c(st,b)
            if s1 is None: continue
            s2,g2=apply_cdag(s1,a)
            if s2 is None: continue
            M[idx[s2],si]+=g1*g2
    return M
Sp=Splus(); Sz=np.array([sum(so[x][1] for x in st)/2 for st in states])
S2=Sp.conj().T@Sp+np.diag(Sz**2-Sz)  # S-=S+^dag; S^2=S-S+ + Sz^2+Sz ; S-S+ = S+^dag S+ ; use Sz(Sz+1)? fix below
S2=Sp.conj().T@Sp+np.diag(Sz**2)-np.diag(Sz)*0
pickle.dump((H1,Hk,states,Sp),open('/tmp/tsbench-run-de_x16pn/mats.pkl','wb'))
print("built",len(states), np.abs(Hk[2]-Hk[2].conj().T).max())
EOF
cd $D && timeout 900 python3 ni.py
