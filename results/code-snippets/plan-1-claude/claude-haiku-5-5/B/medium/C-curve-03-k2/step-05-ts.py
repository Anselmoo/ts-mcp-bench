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
# spin-orbitals
so=[(m,s) for m in ms for s in (+1,-1)]
idx={o:i for i,o in enumerate(so)}
NS=10
def Vtab(B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9; F={0:0.0,2:F2,4:F4}
    # F0 irrelevant constant (set 0); keep A out
    V={}
    for a,b,c,d in itertools.product(range(NS),repeat=4):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
        if sa!=sc or sb!=sd: continue
        v=sum(F[k]*ang(k,ma,mb,mc,md) for k in (2,4))
        if abs(v)>1e-12: V[(a,b,c,d)]=v
    return V
def states():
    return [s for s in itertools.combinations(range(NS),7)]
def apply(ops, st):
    # ops: list of ('c' or 'a', index) applied right-to-left order given as list in application order
    occ=list(st); sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            # insert sorted
            p=sum(1 for j in occ if j<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
def build(Dq,V,P):
    S=states(); index={s:i for i,s in enumerate(S)}
    H=np.zeros((len(S),len(S)))
    for j,st in enumerate(S):
        # one-electron
        for a in range(NS):
            for b in range(NS):
                if so[a][1]!=so[b][1]: continue
                h=P[so[a][0]+2, so[b][0]+2]
                if abs(h)<1e-14: continue
                r,sg=apply([('a',b),('c',a)],st)
                if r is None: continue
                H[index[r],j]+=sg*h
        # two-electron: 1/2 sum V_abcd a+_a a+_b a_d a_c
        for (a,b,c,d),v in V.items():
            r,sg=apply([('a',c),('a',d),('c',b),('c',a)],st)
            if r is None: continue
            H[index[r],j]+=0.5*sg*v
    return S,H
# one-electron projector in m-basis (rows/cols indexed by m+2)
def proj(Dq):
    P=np.zeros((5,5),complex)
    def add(vec,coef):
        v=np.array(vec,complex); P[:,:]+=coef*np.outer(v,v.conj())
    s2=1/np.sqrt(2)
    # eg
    add([0,0,1,0,0],6*Dq)
    add([s2,0,0,0,s2],6*Dq)
    # t2g
    add([0,s2,0,-s2,0],-4*Dq)  # xz
    add([0,1j*0+1/(1j*np.sqrt(2)),0,1/(1j*np.sqrt(2)),0],-4*Dq)  # yz
    add([1/(1j*np.sqrt(2)),0,0,0,-1/(1j*np.sqrt(2))],-4*Dq)  # xy
    return P
