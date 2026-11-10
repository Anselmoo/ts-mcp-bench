
mkdir -p ~/ni && cd ~/ni && cat << 'EOF' > ni.py
import numpy as np, itertools
from scipy.optimize import fsolve
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
orbs=[c*x*y, c*y*z, c*z*x, np.sqrt(5/(16*np.pi))*(3*z*z-1), np.sqrt(15/(16*np.pi))*(x*x-y*y)]
O=np.array(orbs)
G=np.clip(P@P.T,-1,1)
rho=np.einsum('an,cn,n->acn',O,O,W)
A={}
for k in (0,2,4):
    Pk=eval_legendre(k,G)
    A[k]=np.einsum('acn,nm,bdm->acbd', rho, Pk, rho, optimize=True)
print("check Ang0 diag:", np.round(A[0][0,0,0,0],6), np.round(A[0][0,0,1,1],6))
def Vt_of(B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    return F2*A[2]+F4*A[4]   # F0 irrelevant for triplet splittings (constant)
def apply_ops(s, ops):
    # ops list applied right-to-left as given: list of (type,index) in order of application
    sg=1; st=s
    for typ,ix in ops:
        n=bin(st & ((1<<ix)-1)).count('1')
        if typ=='a':
            if not (st>>ix)&1: return 0,None
            sg*=(-1)**n; st&=~(1<<ix)
        else:
            if (st>>ix)&1: return 0,None
            sg*=(-1)**n; st|=(1<<ix)
    return sg,st
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
    # 1/2 sum V_ijkl c+_i c+_j c_l c_k ; <ij|V|kl> = delta(si,sk)delta(sj,sl) Vt[oi,ok,oj,ol]
    for i,s in enumerate(basis):
        for a in range(10):
            for b in range(10):
                for cc_ in range(10):
                    for d in range(10):
                        # k=cc_ (annihilate first), l=d ; amplitude <ab|V|cc_ d>
                        if a%2!=cc_%2 or b%2!=d%2: continue
                        v=Vt[a//2,cc_//2,b//2,d//2]
                        if abs(v)<1e-14: continue
                        # apply c_k then c_l? operator c+_a c+_b c_d c_cc : annihilate cc_ first? order: c_l c_k with k=cc_, l=d
                        sg,st=apply_ops(s,[('a',cc_),('a',d),('c',b),('c',a)][::-1][::-1])
                        # apply order: first c_l? we apply in order: a(d) then a(cc_), but operator is c_d c_cc (rightmost cc acts first)
                        sg,st=apply_ops(s,[('a',cc_)])
                        if sg==0: continue
                        sg2,st2=apply_ops(st,[('a',d)])
                        if sg2==0: continue
                        sg3,st3=apply_ops(st2,[('c',b)])
                        if sg3==0: continue
                        sg4,st4=apply_ops(st3,[('c',a)])
                        if sg4==0: continue
                        H[idx[st4],i]+=0.5*v*sg*sg2*sg3*sg4
    # symmetrize check
    return H, basis
if __name__=="__main__":
    H,b=energies(0.0,1.0,4.5)
    print(np.round(np.linalg.eigvalsh(H),4))
EOF
python3 ni.py