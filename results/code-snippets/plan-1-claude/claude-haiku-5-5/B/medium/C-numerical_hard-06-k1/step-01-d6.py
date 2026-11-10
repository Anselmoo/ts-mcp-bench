import numpy as np, itertools
from scipy.optimize import least_squares
from scipy.special import sph_harm
# real d orbitals on a grid (angular integrals)
rng=np.random.default_rng(0)
N=60
x,w=np.polynomial.legendre.leggauss(N)
phi=np.linspace(0,2*np.pi,2*N,endpoint=False)
th=np.arccos(x)
T,P=np.meshgrid(th,phi,indexing='ij'); W=np.outer(w,np.ones(2*N))*(2*np.pi/(2*N))
X=np.sin(T)*np.cos(P);Y=np.sin(T)*np.sin(P);Z=np.cos(T)
d={'z2':(3*Z**2-1)/2*np.sqrt(5/(4*np.pi))*0+ (3*Z**2-1)/np.sqrt(4*np.pi)*np.sqrt(5)/2,
 'xz':np.sqrt(15/(4*np.pi))*X*Z,'yz':np.sqrt(15/(4*np.pi))*Y*Z,
 'xy':np.sqrt(15/(4*np.pi))*X*Y,'x2y2':np.sqrt(15/(4*np.pi))/2*(X**2-Y**2)}
names=['z2','xz','yz','xy','x2y2']
# Y_kq real basis via complex sph_harm
def realY(k,q):
    # returns function values on grid for real harmonic index q (-k..k)
    out={}
    for m in range(-k,k+1):
        out[m]=sph_harm(m,k,P,T)
    return out
def Ykq_complex(k,m): return sph_harm(m,k,P,T)
# angular factor: <a b|1/r12|c d> = sum_k F^k * (4pi/(2k+1)) sum_q <a|C_kq|c><b|C_kq*|d>
# where C_kq = sqrt(4pi/(2k+1)) Y_kq ; use complex Y and sum over q
def ang(k):
    # Gaunt-type tensor G[a,c,b,d] for real orbitals
    M={}
    Yc={m:sph_harm(m,k,P,T) for m in range(-k,k+1)}
    # matrix elements ∫ d_a* Y_km d_c
    A=np.zeros((k*2+1,5,5),complex)
    for i,m in enumerate(range(-k,k+1)):
        for a in range(5):
            for c in range(5):
                A[i,a,c]=np.sum(W*d[names[a]]*Yc[m]*d[names[c]])
    G=np.zeros((5,5,5,5),complex)
    for a in range(5):
     for c in range(5):
      for b in range(5):
       for dd in range(5):
        s=0
        for i,m in enumerate(range(-k,k+1)):
            # <b|Y_km^*|d>
            s+=A[i,a,c]*np.sum(W*d[names[b]]*np.conj(Yc[m])*d[names[dd]])
        G[a,c,b,dd]=s*4*np.pi/(2*k+1)
    return G
G={k:ang(k) for k in (0,2,4)}
np.save('/tmp/G.npy',np.array([G[0].real,G[2].real,G[4].real]))
print(np.abs(G[2].imag).max(), np.abs(G[4].imag).max())
