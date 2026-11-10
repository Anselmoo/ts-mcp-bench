import numpy as np, itertools, scipy.sparse as sp
from sympy.physics.wigner import gaunt
from scipy.special import sph_harm_y
ms=list(range(-2,3))
def a(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        s+= float(gaunt(2,k,2,-m1,-q,m3)*gaunt(2,k,2,-m2,q,m4))*(-1)**(m1+q+m2)
    return 4*np.pi/(2*k+1)*s
Acoef={(m1,m2,m3,m4):np.array([a(k,m1,m2,m3,m4) for k in (0,2,4)]) for m1,m2,m3,m4 in itertools.product(ms,repeat=4)}
th,wt=np.polynomial.legendre.leggauss(40)
phis=np.linspace(0,2*np.pi,80,endpoint=False)
T,P=np.meshgrid(np.arccos(th),phis,indexing='ij')
W=np.outer(wt,np.ones(len(phis)))*(2*np.pi/len(phis))
x=np.sin(T)*np.cos(P); y=np.sin(T)*np.sin(P); z=np.cos(T)
V=np.zeros_like(T)
for L in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
    c=x*L[0]+y*L[1]+z*L[2]; V+=35*c**4/8-30*c**2/8+3/8
M1=np.zeros((5,5))
for i,m1 in enumerate(ms):
    for j,m2 in enumerate(ms):
        M1[i,j]=np.real(np.sum(np.conj(sph_harm_y(2,m1,T,P))*V*sph_harm_y(2,m2,T,P)*W))
nso=10; N=1<<nso
def ann(p):
    rows=[];cols=[];vals=[]
    for st in range(N):
        if (st>>p)&1:
            rows.append(st^(1<<p)); cols.append(st); vals.append((-1)**bin(st&((1<<p)-1)).count('1'))
    return sp.csr_matrix((vals,(rows,cols)),shape=(N,N))
ANN=[ann(p) for p in range(nso)]; CRE=[X.T.tocsr() for X in ANN]
so=lambda mi,s: 2*mi+s
pop=np.array([bin(s).count('1') for s in range(N)]); idx5=np.where(pop==5)[0]
szd=np.array([sum((0.5 if (s>>(2*i))&1 else 0)-(0.5 if (s>>(2*i+1))&1 else 0) for i in range(5)) for s in range(N)])
Sp=sp.csr_matrix((N,N))
for i in range(5): Sp=Sp+CRE[so(i,0)]@ANN[so(i,1)]
Sz=sp.diags(szd); S2=Sp.T@Sp+Sz@Sz+Sz
# one-body and two-body operator pieces (linear in Dq, F2, F4)
Hone=[]; 
for i in range(5):
    for j in range(5):
        for s in (0,1):
            Hone.append((M1[i,j]*6, CRE[so(i,s)]@ANN[so(j,s)]))
Hone_mat=sum(c*O for c,O in Hone)  # coefficient of Dq
Htwo=[np.zeros(3)]
Ops=[sp.csr_matrix((N,N)) for _ in range(3)]
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    cvec=Acoef[(m1,m2,m3,m4)]
    if np.abs(cvec).max()<1e-12: continue
    for s1 in (0,1):
        for s2 in (0,1):
            O=0.5*(CRE[so(m1+2,s1)]@CRE[so(m2+2,s2)]@ANN[so(m4+2,s2)]@ANN[so(m3+2,s1)])
            for k in range(3): Ops[k]=Ops[k]+cvec[k]*O
Hsub=lambda X: X[idx5][:,idx5].toarray()
Ho=Hsub(Hone_mat); Ok=[Hsub(O) for O in Ops]; S2s=Hsub(S2)
np.savez('<SANDBOX_TMP>/ops.npz',Ho=Ho,O0=Ok[0],O2=Ok[1],O4=Ok[2],S2=S2s)
print("saved; dim",Ho.shape)
