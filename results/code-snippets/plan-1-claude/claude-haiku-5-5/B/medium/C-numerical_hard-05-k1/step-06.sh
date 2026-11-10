cat > /dev/null << 'EOF'
EOF
python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
nt, nphi = 24, 48
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm_y(l, m, TH, PH)
ms=list(range(-2,3))
Ylm={m:Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
def G(m1,m3,k,q): return integ(np.conj(Ylm[m1])*np.conj(Y(k,q))*Ylm[m3])
def H(m2,m4,k,q): return integ(np.conj(Ylm[m2])*Y(k,q)*Ylm[m4])
def angular(k):
    A=np.zeros((5,5,5,5),complex)
    for a,b,c,d in itertools.product(range(5),repeat=4):
        s=0
        for q in range(-k,k+1):
            s+=G(ms[a],ms[c],k,q)*H(ms[b],ms[d],k,q)
        A[a,b,c,d]=4*np.pi/(2*k+1)*s
    return A
A2=angular(2); A4=angular(4)
# sanity: A2 for (m,m,m,m) etc: check Slater F2 ratio: a known value: <22|1/r|22> angular = 4/49*? (F2 coefficient for same orbital is 1/49*... ) print
print("A2[2,2,2,2]",A2[4,4,4,4].real, "A4[4,4,4,4]",A4[4,4,4,4].real)
EOF