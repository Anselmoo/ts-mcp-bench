mkdir -p /tmp/w && cd /tmp/w && cat > d3.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import fsolve, brentq
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.linspace(0,2*np.pi,nph,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def cY(m): return sph_harm(m,2,PH,TH)
s2=1/np.sqrt(2)
Y={m:cY(m) for m in range(-2,3)}
orbs=[1j*(Y[-2]-Y[2])*s2, 1j*(Y[-1]+Y[1])*s2, (Y[-1]-Y[1])*s2, (Y[-2]+Y[2])*s2, Y[0]]
for i in range(5):
    orbs[i]=orbs[i]/np.sqrt(np.sum(W*np.abs(orbs[i])**2))
def ak(k):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Yk=sph_harm(q,k,PH,TH)
        M=np.array([[np.sum(W*np.conj(orbs[a])*np.conj(Yk)*orbs[c]) for c in range(5)] for a in range(5)])
        N=np.array([[np.sum(W*np.conj(orbs[b])*Yk*orbs[d]) for d in range(5)] for b in range(5)])
        A+=np.einsum('ac,bd->abcd',M,N)
    return (4*np.pi/(2*k+1)*A).real
a2,a4=ak(2),ak(4)
# check a2 for d-shell: a^2 for (xy,xy,xy,xy) etc - just print diagonal
NS=10
states=list(itertools.combinations(range(NS),3))
idx={s:i for i,s in enumerate(states)}
D=len(states)
def cann(x,occ):
    if x not in occ: return None
    pos=occ.index(x); return (-1)**pos, occ[:pos]+occ[pos+1:]
def ccre(x,occ):
    if x in occ: return None
    pos=sum(1 for y in occ if y<x); return (-1)**pos, sorted(occ+[x])
def apply2(p,q,r,s,st):
    # c+_p c+_q c_s c_r
    occ=list(st)
    o=cann(r,occ)
    if o is None: return None
    sg1,occ=o; o=cann(s,occ)
    if o is None: return None
    sg2,occ=o; o=ccre(q,occ)
    if o is None: return None
    sg3,occ=o; o=ccre(p,occ)
    if o is None: return None
    sg4,occ=o
    return sg1*sg2*sg3*sg4, tuple(occ)
def apply1(p,q,st):
    occ=list(st); o=cann(q,occ)
    if o is None: return None
    sg1,occ=o; o=ccre(p,occ)
    if o is None: return None
    sg2,occ=o
    return sg1*sg2, tuple(occ)
def twobody(F2,F4):
    G=F2*a2+F4*a4
    H=np.zeros((D,D))
    for p in range(NS):
     for q in range(NS):
      for r in range(NS):
       for s in range(NS):
        if (p%2)!=(r%2) or (q%2)!=(s%2): continue
        val=0.5*G[p//2,q//2,r//2,s//2]
        if abs(val)<1e-14: continue
        for j,st in enumerate(states):
            o=apply2(p,q,r,s,st)
            if o is None: continue
            H[idx[o[1]],j]+=o[0]*val
    return H
def field():
    eps=[-4.0]*3+[6.0]*2   # coefficient of Dq
    H=np.zeros((D,D))
    for j,st in enumerate(states):
        H[j,j]=sum(eps[p//2] for p in st)
    return H
def S2():
    # S^2 = Sz^2 + (S+S- + S-S+)/2 ; S+ = sum_o c+_{o up} c_{o dn}
    Sz=np.diag([sum(0.5 if p%2==0 else -0.5 for p in st) for st in states])
    Sp=np.zeros((D,D)); Sm=np.zeros((D,D))
    for o in range(5):
        for j,st in enumerate(states):
            r=apply1(2*o,2*o+1,st)  # c+_up c_dn : S+
            if r is not None: Sp[idx[r[1]],j]+=r[0]
            r=apply1(2*o+1,2*o,st)
            if r is not None: Sm[idx[r[1]],j]+=r[0]
    return Sz@Sz+0.5*(Sp@Sm+Sm@Sp)+Sz  # S^2 = Sz^2+Sz+S-S+
Sop=S2()
F=field()
T_F2=twobody(1.0,0.0); T_F4=twobody(0.0,1.0)
def levels(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    H=Dq*F+F2*T_F2+F4*T_F4
    H=0.5*(H+H.T)
    out=[]
    w_,v=np.linalg.eigh(Sop)
    for S in [0.75,15/4*0+ 3.75]:
        pass
    res={}
    for Sval in [3.75,0.75]:
        Vs=v[:,np.abs(w_-Sval)<1e-6]
        Hs=Vs.T@H@Vs
        res[Sval]=np.sort(np.linalg.eigvalsh(Hs))
    return res
if __name__=="__main__":
    print("S2 eig:",np.unique(np.round(np.linalg.eigvalsh(Sop),6)))
    r=levels(1.0,0.0,0.0)
    print("Dq=1, B=C=0 quartets:",r[3.75]-0)
    print("doublets", np.unique(np.round(levels(1,0,0)[0.75],6)) if 0 else "")
EOF
python3 d3.py