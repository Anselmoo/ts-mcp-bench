
cd /tmp/tsbench-run-byaa6kok && rm -f x_test && cat << 'EOF' > ni.py
import numpy as np, itertools
from scipy.special import eval_legendre
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
pts=[];w=[]
for ct,wt in zip(xg,wg):
    st=np.sqrt(1-ct*ct)
    for j in range(nphi):
        ph=2*np.pi*j/nphi
        pts.append([st*np.cos(ph),st*np.sin(ph),ct]); w.append(wt*2*np.pi/nphi)
P=np.array(pts); W=np.array(w)
x,y,z=P.T
c=np.sqrt(15/(4*np.pi))
O=np.array([c*x*y, c*y*z, c*z*x, np.sqrt(5/(16*np.pi))*(3*z*z-1), np.sqrt(15/(16*np.pi))*(x*x-y*y)])
G=np.clip(P@P.T,-1,1)
rho=np.einsum('an,cn,n->acn',O,O,W)
A={}
for k in (0,2,4):
    A[k]=np.einsum('acn,nm,bdm->acbd', rho, eval_legendre(k,G), rho, optimize=True)
def Vt_of(B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    return F2*A[2]+F4*A[4]
def apply(s, typ, ix):
    if typ=='a':
        if not (s>>ix)&1: return 0,None
    else:
        if (s>>ix)&1: return 0,None
    n=bin(s & ((1<<ix)-1)).count('1')
    return (-1)**n, (s & ~(1<<ix)) if typ=='a' else (s | (1<<ix))
def energies(Dq,B,C,ne=8,nup=5):
    eps=np.array([(-6*Dq if o>=3 else 4*Dq) for o in range(5) for _ in (0,1)])
    Vt=Vt_of(B,C)
    basis=[sum(1<<i for i in cc) for cc in itertools.combinations(range(10),ne)]
    basis=[s for s in basis if bin(s & 0b0101010101).count('1')==nup]
    idx={s:i for i,s in enumerate(basis)}
    n=len(basis); H=np.zeros((n,n))
    for i,s in enumerate(basis):
        for p in range(10):
            if (s>>p)&1: H[i,i]+=eps[p]
    for i,s in enumerate(basis):
        for a in range(10):
            for b in range(10):
                for k in range(10):
                    for l in range(10):
                        if a%2!=k%2 or b%2!=l%2: continue
                        v=Vt[a//2,k//2,b//2,l//2]
                        if abs(v)<1e-14: continue
                        # operator c+_a c+_b c_l c_k
                        sg=1; st=s; ok=True
                        for typ,ix in (('a',k),('a',l),('c',b),('c',a)):
                            f,st=apply(st,typ,ix)
                            if f==0: ok=False;break
                            sg*=f
                        if ok:
                            H[idx[st],i]+=0.5*v*sg
    return H, basis
if __name__=="__main__":
    H,b=energies(0.0,1.0,4.5)
    print("symmetric:", np.allclose(H,H.T))
    print(np.round(np.linalg.eigvalsh(H),4))
EOF
python3 ni.py