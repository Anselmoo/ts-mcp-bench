import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
# spin-orbitals: (m, s) s=+1/2 -> index
so=[(m,s) for s in (+0.5,-0.5) for m in ms]   # 10 spin orbitals
N=len(so)
# angular quadrature
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.linspace(0,2*np.pi,nph,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
def Y(l,m,t,p): return sph_harm_y(l,m,t,p)
# angular integrals I_k[a,c,q] = int Y_2a^* Y_kq^* Y_2c dOmega ; use index q in -k..k
def Ang(k):
    A=np.zeros((5,5,2*k+1),complex)
    for i,a in enumerate(ms):
        for j,c in enumerate(ms):
            for qi,q in enumerate(range(-k,k+1)):
                A[i,j,qi]=np.sum(W*np.conj(Y(2,a,TH,PH))*np.conj(Y(k,q,TH,PH))*Y(2,c,TH,PH))
    return A
A2,A4=Ang(2),Ang(4)
def Vel(k,F):
    # <ab|V|cd> spatial, a,b,c,d in 0..4 ; sum_q [int Ya* Ykq* Yc][int Yb* Ykq Yd]
    A=A2 if k==2 else A4
    # second factor: int Yb^* Y_kq Yd = conj( int Yd^* Y_kq^* Yb ) ; compute directly
    return A
def Bang(k):
    B=np.zeros((5,5,2*k+1),complex)
    for i,a in enumerate(ms):
        for j,c in enumerate(ms):
            for qi,q in enumerate(range(-k,k+1)):
                B[i,j,qi]=np.sum(W*np.conj(Y(2,a,TH,PH))*Y(k,q,TH,PH)*Y(2,c,TH,PH))
    return B
B2,B4=Bang(2),Bang(4)
def Vspatial(F2,F4):
    V=np.zeros((5,5,5,5),complex)
    for k,Fk,A,B in ((2,F2,A2,B2),(4,F4,A4,B4)):
        pref=4*np.pi/(2*k+1)*Fk
        # sum_q A[a,c,q]*B[b,d,q]   (B uses Y_kq, second electron)
        V+=pref*np.einsum('acq,bdq->abcd',A,B)
    return V
# Fock: determinants of 3 electrons in 10 spin-orbitals
dets=[frozenset(c) for c in itertools.combinations(range(N),3)]
idx={d:i for i,d in enumerate(dets)}
def sgn_apply(ops,state):
    # ops: list of ('c',i) creation or ('a',i) annihilation applied right-to-left as list order (leftmost applied last)
    occ=list(sorted(state)); s=1
    st=set(state)
    for typ,i in reversed(ops):   # apply rightmost first
        lst=sorted(st)
        if typ=='a':
            if i not in st: return None,0
            pos=lst.index(i); s*=(-1)**pos; st.remove(i)
        else:
            if i in st: return None,0
            pos=sum(1 for j in lst if j<i); s*=(-1)**pos; st.add(i)
    return frozenset(st),s
def build(F2,F4):
    V=Vspatial(F2,F4)
    H=np.zeros((len(dets),len(dets)),complex)
    # two-body: 1/2 sum <ab|V|cd> c+_a c+_b c_d c_c, with spin delta
    for I,d in enumerate(dets):
        for a in range(N):
            for b in range(N):
                for c in range(N):
                    for e in range(N):
                        ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; me,se=so[e]
                        if sa!=sc or sb!=se: continue
                        val=V[ms.index(ma),ms.index(mb),ms.index(mc),ms.index(me)]
                        if abs(val)<1e-12: continue
                        st,s=sgn_apply([('a',c),('a',e)],d)  # c_c c_e? need c_d c_c ordering
                        continue
    return None
