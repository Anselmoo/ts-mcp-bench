import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def G(ma,mc,k,q):
    if ma-mc!=q: return 0.0
    return float((-1)**(l-ma)*(2*l+1)*wigner_3j(l,k,l,-ma,q,mc)*wigner_3j(l,k,l,0,0,0))
def Vint(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd: return 0.0
    tot=0.0
    for k in (0,2,4):
        s=sum((-1)**q*G(ma,mc,k,q)*G(mb,md,k,-q) for q in range(-k,k+1))
        tot+=F[k]*s
    return tot
# eg projector in m-basis: |0>, (|2>+|-2>)/sqrt2
def Veg_matrix():
    P=np.zeros((5,5))
    idx={m:i for i,m in enumerate(range(-2,3))}
    P[idx[0],idx[0]]=1
    v=np.zeros(5); v[idx[2]]=1/np.sqrt(2); v[idx[-2]]=1/np.sqrt(2)
    P+=np.outer(v,v)
    return P
PEG=Veg_matrix()
def Hmat(F,Dq,nel=3,Sz2=None):
    # one-electron
    h1=np.zeros((10,10))
    for i,(mi,si) in enumerate(orbs):
        for j,(mj,sj) in enumerate(orbs):
            if si==sj:
                oi=mi+2; oj=mj+2
                h1[i,j]=-4*Dq*(oi==oj)+10*Dq*PEG[oi,oj]
    V=np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(10),repeat=4):
        V[a,b,c,d]=Vint(a,b,c,d,F)
    # basis: determinants with nel electrons, Sz2 = 2*Sz (sum of spins up minus down)
    states=[]
    for occ in itertools.combinations(range(10),nel):
        sz=sum(1 if orbs[o][1]==0 else -1 for o in occ)
        if Sz2 is None or sz==Sz2: states.append(occ)
    index={s:i for i,s in enumerate(states)}
    n=len(states); H=np.zeros((n,n))
    for I,occ in enumerate(states):
        for J,ket in enumerate(states):
            val=0.0
            # one-body: c_i^dag c_j acting on ket
            for i in range(10):
                for j in range(10):
                    if h1[i,j]==0: continue
                    # apply c_j then c_i^dag
                    res=apply(ket,[('a',j),('c',i)])
                    if res is None: continue
                    s,st=res
                    if st==occ: val+=s*h1[i,j]
            # two-body 1/2 sum V_abcd c^+_a c^+_b c_d c_c
            for a,b,c,d in itertools.product(range(10),repeat=4):
                if V[a,b,c,d]==0: continue
                res=apply(ket,[('a',c),('a',d),('c',b),('c',a)])
                if res is None: continue
                s,st=res
                if st==occ: val+=0.5*s*V[a,b,c,d]
            H[I,J]=val
    return H,states
def apply(ket,ops):
    # ops applied right to left: list in order of operator product left..right; we apply last first
    occ=list(ket)
    sign=1
    for typ,o in reversed(ops):
        if typ=='a':
            if o not in occ: return None
            p=occ.index(o); sign*= (-1)**p; occ.remove(o)
        else:
            if o in occ: return None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.append(o); occ.sort()
    return sign,tuple(occ)
