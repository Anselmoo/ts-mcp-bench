import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N as sN
from scipy.optimize import least_squares
l=2; ms=[-2,-1,0,1,2]
GC={}
def g(m1,k,m2,q):
    key=(m1,k,m2,q)
    if key not in GC: GC[key]=float(sN(gaunt(l,k,l,m1,q,m2)))
    return GC[key]
def Cel(k,q,ma,mc):
    if -ma+q+mc!=0: return 0.0
    return np.sqrt(4*np.pi/(2*k+1))*(-1)**(ma%2)*g(-ma,k,mc,q)
def Vel(a,b,c,d,F):
    tot=0.0
    for k in (2,4):
        s=sum((-1)**(q%2)*Cel(k,q,a,c)*Cel(k,-q,b,d) for q in range(-k,k+1))
        tot+=F[k]*s
    return tot
def build(Dq,B,C):
    F4=441*C/35.0; F2=49*B+7*C; F={2:F2,4:F4}
    s2=np.sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[ms.index(m)]=c
        return v
    xy=vec({2:1/(1j*s2),-2:-1/(1j*s2)}); yz=vec({1:1j/s2,-1:1j/s2}); zx=vec({1:-1/s2,-1:1/s2})
    z2=vec({0:1}); x2y2=vec({2:1/s2,-2:1/s2})
    Pt=sum(np.outer(v,v.conj()) for v in [xy,yz,zx]); Pe=sum(np.outer(v,v.conj()) for v in [z2,x2y2])
    h=-4*Dq*Pt+6*Dq*Pe
    n=10; V=np.zeros((n,n,n,n))
    for A in range(n):
        for Bb in range(n):
            for Cc in range(n):
                for D in range(n):
                    if A%2!=Cc%2 or Bb%2!=D%2: continue
                    V[A,Bb,Cc,D]=Vel(ms[A//2],ms[Bb//2],ms[Cc//2],ms[D//2],F)
    H1=np.zeros((n,n),complex)
    for i in range(n):
        for j in range(n):
            if i%2==j%2: H1[i,j]=h[i//2,j//2]
    return H1,V
def fermi(det,ops):
    occ=list(det); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
def basis(Ms2):
    return [c for c in itertools.combinations(range(10),3) if sum(1 for i in c if i%2==0)-(3-sum(1 for i in c if i%2==0))==Ms2]
def Hmat(dets,H1,V):
    idx={d:i for i,d in enumerate(dets)}; n=10
    M=np.zeros((len(dets),len(dets)),complex)
    for j,d in enumerate(dets):
        for i in range(n):
            for jj in range(n):
                if H1[i,jj]==0: continue
                nd,s=fermi(d,[('c',i),('a',jj)])
                if nd is not None and nd in idx: M[idx[nd],j]+=H1[i,jj]*s
        for a in range(n):
         for b in range(n):
          for c in range(n):
           for dd in range(n):
            v=V[a,b,c,dd]
            if abs(v)<1e-12: continue
            nd,s=fermi(d,[('c',a),('c',b),('a',dd),('a',c)])
            if nd is not None and nd in idx: M[idx[nd],j]+=0.5*v*s
    return M
Mq0=basis(3); Md0=basis(1)
def spectrum(Dq,B,C):
    H1,V=build(Dq,B,C)
    Mq=Hmat(Mq0,H1,V); Md=Hmat(Md0,H1,V)
    eq=np.sort(np.linalg.eigvalsh((Mq+Mq.conj().T)/2))
    ed=np.sort(np.linalg.eigvalsh((Md+Md.conj().T)/2))
    rest=list(ed)
    for e in eq:
        k=int(np.argmin([abs(x-e) for x in rest])); rest.pop(k)
    rest=np.array(rest)
    g0=eq[0]
    return eq-g0, rest-g0
# model: 4T2=10Dq; 4T1F, 4T1P; lowest doublet
def model(p):
    Dq,B,C=p
    q,d=spectrum(Dq,B,C)
    t2=q[1]; t1f=q[4]; t1p=q[7]; e2=d[0]
    return np.array([t2,t1f,t1p,e2])
obs=np.array([14490,20430,32030,12710.])
res=least_squares(lambda p: model(p)-obs, x0=[1450,700,3500], xtol=1e-12, ftol=1e-12)
print("fit Dq,B,C:",np.round(res.x,1))
print("model:",np.round(model(res.x),1),"obs:",obs)
print("full quartet/doublet at fit:")
q,d=spectrum(*res.x)
print(np.round(q,0)); print(np.round(d[:9],0))
