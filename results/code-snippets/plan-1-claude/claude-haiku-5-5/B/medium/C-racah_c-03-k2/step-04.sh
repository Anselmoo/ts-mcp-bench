mkdir -p /tmp/w && cat > /tmp/w/d3.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (+1,-1) for m in ms]   # spin-orbitals (m, spin)
N=len(so)
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.linspace(0,2*np.pi,nph,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
def Y(l,m,t,p): return sph_harm_y(l,m,t,p)
def ang(k,conj1):
    A=np.zeros((5,5,2*k+1),complex)
    for i,a in enumerate(ms):
        for j,c in enumerate(ms):
            for qi,q in enumerate(range(-k,k+1)):
                if conj1:  # int Ya* Ykq* Yc
                    A[i,j,qi]=np.sum(W*np.conj(Y(2,a,TH,PH))*np.conj(Y(k,q,TH,PH))*Y(2,c,TH,PH))
                else:      # int Yb* Ykq Yd
                    A[i,j,qi]=np.sum(W*np.conj(Y(2,a,TH,PH))*Y(k,q,TH,PH)*Y(2,c,TH,PH))
    return A
A={k:ang(k,True) for k in (2,4)}; B={k:ang(k,False) for k in (2,4)}
def Vspatial(F2,F4):
    V=np.zeros((5,5,5,5),complex)
    for k,Fk in ((2,F2),(4,F4)):
        V+=4*np.pi/(2*k+1)*Fk*np.einsum('acq,bdq->abcd',A[k],B[k])
    return V
def apply(ops,state):
    # ops in operator order; apply rightmost first. returns (newstate, sign) or (None,0)
    st=set(state); s=1
    for typ,i in reversed(ops):
        lst=sorted(st); pos=sum(1 for j in lst if j<i)
        if typ=='a':
            if i not in st: return None,0
            s*=(-1)**pos; st.remove(i)
        else:
            if i in st: return None,0
            s*=(-1)**pos; st.add(i)
    return frozenset(st),s
dets=[frozenset(c) for c in itertools.combinations(range(N),3)]
idx={d:i for i,d in enumerate(dets)}
D=len(dets)
def build(F2,F4,Dq):
    V=Vspatial(F2,F4)
    H=np.zeros((D,D),complex)
    # two-body
    for J,d in enumerate(dets):
        for a in range(N):
            for b in range(N):
                for c in range(N):
                    for e in range(N):
                        sa=so[a][1]; sb=so[b][1]; sc=so[c][1]; se=so[e][1]
                        if sa!=sc or sb!=se: continue
                        val=V[ms.index(so[a][0]),ms.index(so[b][0]),ms.index(so[c][0]),ms.index(so[e][0])]
                        if abs(val)<1e-13: continue
                        # c+_a c+_b c_d c_c with <ab|V|cd>, here d=e
                        ns,s=apply([('c',a),('c',b),('a',e),('a',c)],d)
                        if ns is None: continue
                        I=idx[ns]; H[I,J]+=0.5*val*s
    # one-body CF: operator matrix h (spatial), spin diagonal
    h=CFmat(Dq)
    for J,d in enumerate(dets):
        for a in range(N):
            for b in range(N):
                if so[a][1]!=so[b][1]: continue
                val=h[ms.index(so[a][0]),ms.index(so[b][0])]
                if abs(val)<1e-13: continue
                ns,s=apply([('c',a),('a',b)],d)
                if ns is None: continue
                H[idx[ns],J]+=val*s
    return H
def CFmat(Dq):
    # octahedral: eg (dz2, dx2-y2) at +6Dq, t2g at -4Dq, in complex basis via projector construction
    # build from real-orbital definitions
    s2=np.sqrt(2)
    # complex basis ordering ms=-2..2 ; real orbitals as combinations
    def vec(d): return np.array([d.get(m,0) for m in ms],complex)
    xy=vec({2:1/(1j*s2)*0,})  # placeholder
    # real harmonics: dz2 = m0 ; dxz,dyz (m=±1); dx2-y2,dxy (m=±2)
    dz2=vec({0:1})
    dxz=vec({1:-1/s2,-1:1/s2}); dyz=vec({1:-1j/s2,-1:-1j/s2})
    dx2=vec({2:1/s2,-2:1/s2}); dxy=vec({2:-1j/s2,-2:1j/s2})
    eg=[dz2,dx2]; t2g=[dxz,dyz,dxy]
    P=np.zeros((5,5),complex)
    for v in eg: P+=6*Dq*np.outer(v,np.conj(v))
    for v in t2g: P+=-4*Dq*np.outer(v,np.conj(v))
    return P
EOF
cd /tmp/w && python3 -c "
import d3,numpy as np
P=d3.CFmat(1.0); print(np.round(np.linalg.eigvalsh(P),6))
"