rm -f t && cat > d3.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
import scipy.sparse as sp
xg,wg=np.polynomial.legendre.leggauss(30)
phis=np.linspace(0,2*np.pi,60,endpoint=False); wp=2*np.pi/60
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij'); W=np.outer(wg,np.ones(len(phis)))*wp
ms=list(range(-2,3))
def Y(k,q): return sph_harm_y(k,q,TH,PH)
Yc={m:Y(2,m) for m in ms}
Vc={k:np.zeros((5,5,5,5),complex) for k in (0,2,4)}
for k in (2,4):
  Ykq={q:Y(k,q) for q in range(-k,k+1)}
  for ia,a in enumerate(ms):
    for ic,c in enumerate(ms):
      G1={q:np.sum(W*np.conj(Yc[a])*Yc[c]*np.conj(Ykq[q])) for q in range(-k,k+1)}
      for ib,b in enumerate(ms):
        for id_,d in enumerate(ms):
          s=0
          for q in range(-k,k+1):
            s+=G1[q]*np.sum(W*np.conj(Yc[b])*Yc[d]*Ykq[q])
          Vc[k][ia,ib,ic,id_]=4*np.pi/(2*k+1)*s
s2=np.sqrt(2); I=1j
U=np.zeros((5,5),complex)
U[0,0]=1/(I*s2); U[0,4]=-1/(I*s2)      # xy
U[1,1]=1/(I*s2); U[1,3]=1/(I*s2)       # yz
U[2,1]=-1/s2;    U[2,3]=1/s2           # xz
U[3,2]=1                               # z2
U[4,0]=1/s2;     U[4,4]=1/s2           # x2-y2
assert np.allclose(U@U.conj().T,np.eye(5))
Vr={k:np.einsum('ai,bj,ck,dl,ijkl->abcd',U.conj(),U.conj(),U,U,Vc[k]) for k in (2,4)}
N=10
def cop(i):
    dim=2**N; rows=[];cols=[];vals=[]
    for s in range(dim):
        if (s>>i)&1:
            sign=(-1)**bin(s & ((1<<i)-1)).count('1')
            rows.append(s^(1<<i)); cols.append(s); vals.append(sign)
    return sp.csr_matrix((vals,(rows,cols)),shape=(dim,dim))
c=[cop(i) for i in range(N)]
cd=[x.T.tocsr() for x in c]
states=[s for s in range(2**N) if bin(s).count('1')==3]
def restrict(M): return M[states][:,states]
# precompute one-body number ops and two-body products
nops=[restrict(cd[i]@c[i]) for i in range(N)]
pairs={}
TB=[]  # list of (coef-matrix index,...) 
two={}
for o1,o2,o3,o4 in itertools.product(range(5),repeat=4):
    for s1 in range(2):
        for s2_ in range(2):
            a=2*o1+s1; b=2*o2+s2_; cc=2*o3+s1; dd=2*o4+s2_
            key=(o1,o2,o3,o4)
            two.setdefault(key,[]).append((a,b,cc,dd))
TWO={}
for key,lst in two.items():
    tot=None
    for (a,b,cc,dd) in lst:
        M=restrict(cd[a]@cd[b]@c[dd]@c[cc])
        tot=M if tot is None else tot+M
    TWO[key]=tot
def build_H(Dq,B,C,F0=0.0):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    Fk={2:F2,4:F4}
    eps=[-4*Dq,-4*Dq,-4*Dq,6*Dq,6*Dq]
    H=sum(eps[o]*(nops[2*o]+nops[2*o+1]) for o in range(5))
    H=H.toarray() if sp.issparse(H) else H
    for key,M in TWO.items():
        v=sum(Fk[k]*Vr[k][key] for k in (2,4))
        if abs(v)>1e-12:
            H=H+0.5*v*M.toarray()
    return H
if __name__=="__main__":
    H=build_H(0,1.0,0.0)
    print(np.round(np.linalg.eigvalsh(H),6)[:10])
EOF
time python3 d3.py