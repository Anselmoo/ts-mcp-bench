import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
N=10
def Ang(mi,mk,K,q):
    if -mi+mk-q!=0 or abs(q)>K: return 0.0
    return (-1)**(mi)*((-1)**q)*float(gaunt(2,2,K,-mi,mk,-q))
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=np.sqrt(2)
t2g=[vec({-2:1/(1j*r2),2:-1/(1j*r2)}), vec({-1:-1/r2,1:1/r2}), vec({-1:1/(1j*r2),1:1/(1j*r2)})]
eg=[vec({0:1}), vec({-2:1/r2,2:1/r2})]
hu=-4*sum(np.outer(v,v.conj()) for v in t2g)+6*sum(np.outer(v,v.conj()) for v in eg)
def apply_ops(state, ops):
    s=list(state); sign=1
    for typ,p in ops:
        if typ=='a':
            if p not in s: return None,0
            pos=s.index(p); sign*=(-1)**pos; s.pop(pos)
        else:
            if p in s: return None,0
            pos=sum(1 for x in s if x<p); sign*=(-1)**pos; s.insert(pos,p)
    return tuple(s),sign
dets=list(itertools.combinations(range(N),5)); idx={d:n for n,d in enumerate(dets)}
nd=len(dets)
A={(K,q,mi,mk):Ang(mi,mk,K,q) for K in (0,2,4) for q in range(-K,K+1) for mi in ms for mk in ms}
W={}
for i,(mi,si) in enumerate(orbs):
 for k,(mk,sk) in enumerate(orbs):
  if si!=sk: continue
  for j,(mj,sj) in enumerate(orbs):
   for ll,(ml,sl) in enumerate(orbs):
    if sj!=sl: continue
    d={K:4*np.pi/(2*K+1)*sum(((-1)**q)*A[(K,q,mi,mk)]*A[(K,-q,mj,ml)] for q in range(-K,K+1)) for K in (0,2,4)}
    if any(abs(v)>1e-12 for v in d.values()): W[(i,j,k,ll)]=d
M2=np.zeros((nd,nd)); M4=np.zeros((nd,nd)); OD=np.zeros((nd,nd)); Sp=np.zeros((nd,nd))
for n,d in enumerate(dets):
    for (i,j,k,ll),dd in W.items():
        s,sg=apply_ops(d,[('a',k),('a',ll),('c',j),('c',i)])
        if s is not None:
            M2[idx[s],n]+=0.5*sg*dd[2]; M4[idx[s],n]+=0.5*sg*dd[4]
    for i in range(N):
        for k in range(N):
            if orbs[i][1]!=orbs[k][1]: continue
            s,sg=apply_ops(d,[('a',k),('c',i)])
            if s is None: continue
            OD[idx[s],n]+=sg*hu[orbs[i][0]+2,orbs[k][0]+2].real
    for m in ms:
        s,sg=apply_ops(d,[('a',orbs.index((m,1))),('c',orbs.index((m,0)))])
        if s is not None: Sp[idx[s],n]+=sg
Szv=np.array([sum(0.5 if orbs[p][1]==0 else -0.5 for p in d) for d in dets])
S2=Sp.T@Sp+np.diag(Szv**2+Szv)
w,U=np.linalg.eigh(S2)
P=U[:,np.abs(w-0.75)<1e-6]
Md=[P.T@M@P for M in (OD,M2,M4)]
def levels(Dq,B):
    C=4.4*B; F2=49*B+7*C; F4=12.6*C
    e=np.sort(np.linalg.eigvalsh(Dq*Md[0]+F2*Md[1]+F4*Md[2]))
    out=[]
    for x in e:
        if out and abs(x-out[-1][0])<1e-5: out[-1][1]+=1
        else: out.append([x,1])
    g=out[0][0]
    return [(x-g,m//2) for x,m in out]
# Identify lowest three excited distinct levels: A1g(deg1), T1g(3), T2g(3)
def lowest3(Dq,B):
    L=levels(Dq,B)
    ex=[(e,d) for e,d in L if e>1e-3]
    return ex[:4]
obs=np.array([29360.,29620.,31640.])
print(lowest3(2400,600))
def resid(p):
    Dq,B=p
    ex=lowest3(Dq,B)
    return np.array([ex[0][0],ex[1][0],ex[2][0]])-obs
sol=least_squares(resid,[2400,600],x_scale=[1000,100])
print("fit Dq,B:",sol.x, "C=",4.4*sol.x[1], "resid", resid(sol.x))
print("levels:",[(round(e,1),d) for e,d in lowest3(*sol.x)])
