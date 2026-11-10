
cat << 'EOF' > /tmp/d4.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
# quadrature on sphere
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),ph,indexing='ij')
W=(wg[:,None]*np.ones(nphi)[None,:])*(2*np.pi/nphi)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
# real d orbitals (unnormalized angular functions, normalize by quadrature)
orbs={'xy':x*y,'yz':y*z,'zx':z*x,'x2y2':x*x-y*y,'z2':3*z*z-1}
names=list(orbs)
for n in names:
    orbs[n]=orbs[n]/np.sqrt(np.sum(W*orbs[n]**2))
# real spherical harmonics basis for k=0,2,4 via projection on monomials: use complex sph_harm -> real
def realY(l,m,TH,PH):
    if m==0: return sph_harm(0,l,PH,TH).real
    if m>0: return np.sqrt(2)*(-1)**m*sph_harm(m,l,PH,TH).real
    return np.sqrt(2)*(-1)**m*sph_harm(-m,l,PH,TH).imag
def G(k):
    out=[]
    for q in range(-k,k+1):
        out.append(realY(k,q,TH,PH))
    return out
# build angular tensors
dim=5
def Vang(k):
    Yk=G(k)
    # M[a,c,q]=int phi_a phi_c Y_kq
    M=np.zeros((5,5,len(Yk)))
    for i,a in enumerate(names):
        for j,c in enumerate(names):
            for q,Y in enumerate(Yk):
                M[i,j,q]=np.sum(W*orbs[a]*orbs[c]*Y)
    # sum_q M[a,c,q]M[b,d,q] * 4pi/(2k+1)
    return np.einsum('acq,bdq->acbd',M,M)*4*np.pi/(2*k+1)
A0=Vang(0);A2=Vang(2);A4=Vang(4)
# Fock space: 10 spin-orbitals: index = 2*orb + spin
N=10
states=[s for s in range(1<<N) if bin(s).count('1')==4]
idx={s:i for i,s in enumerate(states)}
D=len(states)
def apply_cdag_c(p,q,s):
    # c_p^dag c_q on bit state s, returns (sign,newstate) or None
    if not (s>>q)&1: return None
    sign=1
    t=s
    # annihilate q
    n_below=bin(t & ((1<<q)-1)).count('1')
    sign*= (-1)**n_below
    t&=~(1<<q)
    if (t>>p)&1: return None
    n_below=bin(t & ((1<<p)-1)).count('1')
    sign*=(-1)**n_below
    t|=(1<<p)
    return sign,t
def build(Dq,B,C):
    F4=C*441/35.0
    F2=(B*441+5*F4)/9.0
    # two-electron Vee in orbital basis
    V=F0A=None
    Vee=F2*A2+F4*A4  # F0 omitted (constant for d4 shifts, cancels in differences)
    # one-electron
    h=np.zeros((5,5))
    for i,n in enumerate(names):
        h[i,i]= 6*Dq if n in ('x2y2','z2') else -4*Dq
    # spin-orbital matrices
    H=np.zeros((D,D))
    # one-body
    for s in states:
        j=idx[s]
        for p in range(N):
            for q in range(N):
                if p%2!=q%2: continue
                hv=h[p//2,q//2]
                if hv==0: continue
                r=apply_cdag_c(p,q,s)
                if r is None: continue
                sg,t=r
                H[idx[t],j]+=sg*hv
    # two-body: 1/2 sum V_{abcd} c+_a c+_b c_d c_c, with V_{abcd}=<ab|cd>
    for s in states:
        j=idx[s]
        for a in range(N):
            for b in range(N):
                for c in range(N):
                    for d in range(N):
                        if a%2!=d%2 or b%2!=c%2: continue
                        v=Vee[a//2,d//2,b//2,c//2]
                        if abs(v)<1e-14: continue
                        # c_c first? operator c+_a c+_b c_c c_d ... use c+_a c+_b c_d c_c with <ab|cd>
                        # apply c_c, then c_d, then c+_b, then c+_a
                        r=apply_cdag_c_multi(s,[('c',c),('c',d),('d',b),('d',a)])
                        if r is None: continue
                        sg,t=r
                        H[idx[t],j]+=0.5*sg*v
    return H
def apply_cdag_c_multi(s,ops):
    sign=1; t=s
    for op,i in ops:
        if op=='c':
            if not (t>>i)&1: return None
            sign*=(-1)**bin(t & ((1<<i)-1)).count('1'); t&=~(1<<i)
        else:
            if (t>>i)&1: return None
            sign*=(-1)**bin(t & ((1<<i)-1)).count('1'); t|=(1<<i)
    return sign,t
# S^2 operator
def S2():
    Sz=np.zeros(D); 
    for s in states:
        j=idx[s]; Sz[j]=0.5*sum((1 if (s>>(2*o))&1 else 0)-(1 if (s>>(2*o+1))&1 else 0) for o in range(5))
    # S^2 = Sz^2 + (S+S- + S-S+)/2 ; build S+ S-
    Sp=np.zeros((D,D))
    for s in states:
        for o in range(5):
            r=apply_cdag_c_multi(s,[('d',2*o),('c',2*o+1)])
            if r: Sp[idx[r[1]],idx[s]]+=r[0]
    Sm=Sp.T
    return np.diag(Sz**2)+0.5*(Sp@Sm+Sm@Sp)
S2m=S2()
def triplet_levels(Dq,B,C):
    H=build(Dq,B,C)
    Hh=H+1e6*S2m
    w,v=np.linalg.eigh(Hh)
    # pick S=1 (S2=2)
    e=[]
    for k in range(D):
        if abs(v[:,k]@S2m@v[:,k]-2)<1e-6: e.append(w[k]-1e6*2)
    return np.sort(np.array(e))
if __name__=='__main__':
    import sys
    e=triplet_levels(1000,800,4.3*800)
    print(e[:20]-e[0])
EOF
cd /tmp && time python3 d4.py
