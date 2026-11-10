cat > /tmp/tsbench-home-xehwqch9/../ff.py 2>/dev/null; python3 - << 'EOF'
import numpy as np, itertools, scipy.sparse as sp
from sympy.physics.wigner import gaunt
from scipy.special import sph_harm_y
from scipy.optimize import fsolve
ms=list(range(-2,3))
def a(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        s+= float(gaunt(2,k,2,-m1,-q,m3)*gaunt(2,k,2,-m2,q,m4))*(-1)**(m1+q+m2)
    return 4*np.pi/(2*k+1)*s
Acoef={}
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    Acoef[(m1,m2,m3,m4)]=np.array([a(k,m1,m2,m3,m4) for k in (0,2,4)])
# one-electron cubic matrix (unit: eg=1, t2g=-2/3)
th,wt=np.polynomial.legendre.leggauss(40)
phis=np.linspace(0,2*np.pi,80,endpoint=False)
T,P=np.meshgrid(np.arccos(th),phis,indexing='ij')
W=np.outer(wt,np.ones(len(phis)))*(2*np.pi/len(phis))
x=np.sin(T)*np.cos(P); y=np.sin(T)*np.sin(P); z=np.cos(T)
V=np.zeros_like(T)
for L in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
    c=x*L[0]+y*L[1]+z*L[2]; V+=35*c**4/8-30*c**2/8+3/8
M1=np.zeros((5,5),complex)
for i,m1 in enumerate(ms):
    for j,m2 in enumerate(ms):
        M1[i,j]=np.sum(np.conj(sph_harm_y(2,m1,T,P))*V*sph_harm_y(2,m2,T,P)*W)
M1=M1.real
# spin orbitals: index 2*i+s, i=m index, s=0 up,1 down
nso=10
def ann(p):
    # Jordan-Wigner annihilation on 10 modes
    rows=[];cols=[];vals=[]
    for st in range(1<<nso):
        if st>>p &1:
            sign=(-1)**bin(st & ((1<<p)-1)).count('1')
            rows.append(st^(1<<p)); cols.append(st); vals.append(sign)
    return sp.csr_matrix((vals,(rows,cols)),shape=(1<<nso,1<<nso))
ANN=[ann(p) for p in range(nso)]
CRE=[A.T.tocsr() for A in ANN]
def so(mi,s): return 2*mi+s
# Slater-coefficient tensors for two-electron part: list of (coef_k vector) per (a,b,c,d)
def build(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    Fk=np.array([0.0,F2,F4])
    H=sp.csr_matrix((1<<nso,1<<nso))
    # one-body
    for i in range(5):
        for j in range(5):
            if M1[i,j]!=0:
                for s in (0,1):
                    H=H+6*Dq*M1[i,j]*(CRE[so(i,s)]@ANN[so(j,s)])
    # two-body
    Hd=sp.csr_matrix((1<<nso,1<<nso))
    for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
        coef=Acoef[(m1,m2,m3,m4)]@Fk
        if abs(coef)<1e-12: continue
        for s1 in (0,1):
            for s2 in (0,1):
                a_=so(m1+2,s1); b_=so(m2+2,s2); c_=so(m3+2,s1); d_=so(m4+2,s2)
                # <ab|V|cd>, spin: s_a=s_c, s_b=s_d
                Hd=Hd+0.5*coef*(CRE[a_]@CRE[b_]@ANN[d_]@ANN[c_])
    return H+Hd
EOF
echo done