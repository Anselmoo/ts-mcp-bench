import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N as sN
from scipy.optimize import fsolve
l=2
ms=[(m,s) for m in range(-2,3) for s in (0,1)]
def G(l1,l2,l3,m1,m2,m3): return float(sN(gaunt(l1,l2,l3,m1,m2,m3)))
def Cmat(k,q,ma,mc): return np.sqrt(4*np.pi/(2*k+1))*(-1)**ma*G(l,k,l,-ma,q,mc)
def Vel(k):
    V=np.zeros((10,10,10,10))
    for a,(ma,sa) in enumerate(ms):
      for b,(mb,sb) in enumerate(ms):
        for c,(mc,sc) in enumerate(ms):
          for d,(md,sd) in enumerate(ms):
            if sa!=sc or sb!=sd: continue
            tot=0.0
            for q in range(-k,k+1):
                if ma-mc!=-q or mb-md!=q: continue
                tot+=(-1)**q*Cmat(k,-q,ma,mc)*Cmat(k,q,mb,md)
            V[a,b,c,d]=tot
    return V
Vs={k:Vel(k) for k in [0,2,4]}
s2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
orbs={'z2':vec({0:1}),'x2y2':vec({2:1/s2,-2:1/s2}),
      'xy':vec({2:1j/s2,-2:-1j/s2}),'xz':vec({1:-1/s2,-1:1/s2}),'yz':vec({1:1j/s2,-1:1j/s2})}
h1=np.zeros((10,10),complex)
for name,v in orbs.items():
    e=6.0 if name in('z2','x2y2') else -4.0
    P=np.outer(v,v.conj())
    for i,(mi,si) in enumerate(ms):
        for j,(mj,sj) in enumerate(ms):
            if si==sj: h1[i,j]+=e*P[mi+2,mj+2]
states=list(itertools.combinations(range(10),3))
idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,state):
    occ=list(state); sign=1
    for typ,o in ops:
        if typ=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return tuple(occ),sign
Ms={k:np.zeros((120,120)) for k in [0,2,4]}
Hcf=np.zeros((120,120))
for i,s in enumerate(states):
    for a in range(10):
        for c in range(10):
            if abs(h1[a,c])>1e-14:
                t,sg=apply_ops([('a',c),('c',a)],s)
                if t is not None: Hcf[idx[t],i]+=sg*h1[a,c].real
    for k in [0,2,4]:
        V=Vs[k]
        for a in range(10):
         for b in range(10):
          for c in range(10):
           for d in range(10):
            v=V[a,b,c,d]
            if abs(v)<1e-14: continue
            t,sg=apply_ops([('a',c),('a',d),('c',b),('c',a)],s)
            if t is not None: Ms[k][idx[t],i]+=0.5*sg*v
def opidx(m,s): return ms.index((m,s))
Sp=np.zeros((120,120))
for i,s in enumerate(states):
    for m in range(-2,3):
        t,sg=apply_ops([('a',opidx(m,1)),('c',opidx(m,0))],s)
        if t is not None: Sp[idx[t],i]+=sg
Sz=np.array([sum(0.5 if ms[x][1]==0 else -0.5 for x in s) for s in states])
S2=Sp.T@Sp+np.diag(Sz**2+Sz)
w,vv=np.linalg.eigh(S2)
Q=vv[:,np.abs(w-3.75)<1e-6]; D=vv[:,np.abs(w-0.75)<1e-6]
def build(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    return Dq*Hcf+F2*Ms[2]+F4*Ms[4]
def energies(Dq,B,C):
    H=build(Dq,B,C)
    hq=np.linalg.eigvalsh(Q.T@H@Q); hd=np.linalg.eigvalsh(D.T@H@D)
    return hq,hd
def spectrum(Dq,B,C):
    hq,hd=energies(Dq,B,C)
    g=hq.min()
    T2=hq[np.argmin(np.abs(hq-g-10*Dq))]-g
    # 4T1F: lowest quartet level above 4T2 of multiplicity 12 (3 terms x 4)
    qs=np.unique(np.round(hq,3))
    # quartet levels distinct
    lv=[]
    for x in np.sort(hq):
        if not lv or abs(x-lv[-1][0])>0.5: lv.append([x,1])
        else: lv[-1][1]+=1
    T1F=lv[2][0]-g; T1P=lv[3][0]-g
    # 2E: 4-fold doublet level closest to ~14000 above ground
    dl=[]
    for x in np.sort(hd):
        if not dl or abs(x-dl[-1][0])>0.5: dl.append([x,1])
        else: dl[-1][1]+=1
    E2=[x-g for x,m in dl if m==4]
    return T2,T1F,T1P,E2
print('check', spectrum(1750,600,3000))
def res(p):
    B,C=p
    T2,T1F,T1P,E2=spectrum(1750,B,C)
    return [T1F-23800, E2[0]-14300]
sol=fsolve(res,[600,3000])
print('B,C=',sol, res(sol))
print('spectrum at solution', spectrum(1750,*sol))
