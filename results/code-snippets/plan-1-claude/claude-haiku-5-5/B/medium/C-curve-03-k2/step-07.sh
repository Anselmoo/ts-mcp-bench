
cd /tmp/tsbench-run-me24kyq4 && cat > ts.py <<'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from numpy.polynomial.legendre import leggauss
nt,npn=40,80
x,wt=leggauss(nt); th=np.arccos(x); ph=np.arange(npn)*2*np.pi/npn; wp=2*np.pi/npn
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(wt,np.ones(npn))*wp
def Y(l,m): return sph_harm_y(l,m,TH,PH)
ms=list(range(-2,3)); Yd={m:Y(2,m) for m in ms}
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        g1=np.sum(W*np.conj(Yd[a])*Yd[c]*np.conj(Y(k,q)))
        g2=np.sum(W*np.conj(Yd[b])*Yd[d]*Y(k,q))
        s+=g1*g2
    return (4*np.pi/(2*k+1)*s).real
so=[(m,s) for m in ms for s in (+1,-1)]
NS=10
def Vtab(B,C,nel=None):
    F4=441*C/35; F2=(441*B+5*F4)/9; F={2:F2,4:F4}
    V={}
    for a,b,c,d in itertools.product(range(NS),repeat=4):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
        if sa!=sc or sb!=sd: continue
        v=sum(F[k]*ang(k,ma,mb,mc,md) for k in (2,4))
        if abs(v)>1e-12: V[(a,b,c,d)]=v
    return V
def apply(ops, st):
    occ=list(st); sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            p=sum(1 for j in occ if j<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
def build(nel,V,P):
    S=list(itertools.combinations(range(NS),nel)); index={s:i for i,s in enumerate(S)}
    H=np.zeros((len(S),len(S)),complex)
    for j,st in enumerate(S):
        for a in range(NS):
            for b in range(NS):
                if so[a][1]!=so[b][1]: continue
                h=P[so[a][0]+2, so[b][0]+2]
                if abs(h)<1e-14: continue
                r,sg=apply([('a',b),('c',a)],st)
                if r is None: continue
                H[index[r],j]+=sg*h
        for (a,b,c,d),v in V.items():
            r,sg=apply([('a',c),('a',d),('c',b),('c',a)],st)
            if r is None: continue
            H[index[r],j]+=0.5*sg*v
    return S,H
def proj(Dq):
    P=np.zeros((5,5),complex)
    def add(vec,coef):
        v=np.array(vec,complex); P[:,:]+=coef*np.outer(v,v.conj())
    s2=1/np.sqrt(2)
    add([0,0,1,0,0],6*Dq)
    add([s2,0,0,0,s2],6*Dq)
    add([0,s2,0,-s2,0],-4*Dq)
    add([0,1/(1j*np.sqrt(2)),0,1/(1j*np.sqrt(2)),0],-4*Dq)
    add([1/(1j*np.sqrt(2)),0,0,0,-1/(1j*np.sqrt(2))],-4*Dq)
    return P
def Ssq(S):
    # total spin S^2 operator matrix in determinant basis
    n=len(S); M=np.zeros((n,n),complex)
    # S^2 = Sz^2 + (S+S- + S-S+)/2
    idxs={s:i for i,s in enumerate(S)}
    for j,st in enumerate(S):
        sz=sum(0.5*so[i][1] for i in st); M[j,j]+=sz*sz
        for m in ms:
            up=(m,1); dn=(m,-1)
            iu=so.index(up); idn=so.index(dn)
            # S+S- : a+_up a_dn
            r,sg=apply([('c',iu),('a',idn)],st)
            if r is not None and r in idxs:
                M[idxs[r],j]+=sg*0.5  # S+S- /2 contribution (approx with per-orbital spin ops)
    return M
EOF
python3 -c "
exec(open('ts.py').read())
import numpy as np
# d2 test: P=0 (no field)
V=Vtab(1.0,4.0)
S,H=build(2,V,np.zeros((5,5),complex))
print(sorted(set(np.round(np.linalg.eigvalsh(H),6))))
"