import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from math import sqrt
from scipy.optimize import brentq
l=2
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
N=10
def ang(k,m1,q,m2):
    if m1!=m2+q: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-m1)*float(wigner_3j(l,k,l,-m1,q,m2))*red
ms=list(range(-2,3))
W=np.zeros((5,5))
for i,m1 in enumerate(ms):
    for j,m2 in enumerate(ms):
        W[i,j]=ang(4,m1,0,m2)+sqrt(5/14)*(ang(4,m1,4,m2)+ang(4,m1,-4,m2))
Wcf=21.0*W  # one-electron CF per unit Dq
B,C=621.0,2851.0
F4=441*C/35; F2=(441*B+5*F4)/9
Fk=[0.0,F2,F4]
Vt={}
for a,(ma,sa) in enumerate(orbs):
 for b,(mb,sb) in enumerate(orbs):
  for c,(mc,sc) in enumerate(orbs):
   for d,(md,sd) in enumerate(orbs):
    if sa!=sc or sb!=sd: continue
    tot=0.0
    for k,F in zip((0,2,4),Fk):
        if F==0: continue
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*ang(k,ma,q,mc)*ang(k,mb,-q,md)
        tot+=F*s
    if abs(tot)>1e-12: Vt[(a,b,c,d)]=tot
dets=list(itertools.combinations(range(N),5))
idx={d:i for i,d in enumerate(dets)}
D=len(dets)
def ann(st,i):
    if i not in st: return None
    return (-1)**sum(1 for x in st if x<i), tuple(x for x in st if x!=i)
def cre(st,i):
    if i in st: return None
    return (-1)**sum(1 for x in st if x<i), tuple(sorted(st+(i,)))
def op1(st,a,b):  # a+_a a_b
    r=ann(st,b)
    if r is None: return None
    s1,st1=r
    r=cre(st1,a)
    if r is None: return None
    s2,st2=r
    return s1*s2,st2
def op2(st,a,b,c,d):  # a+_a a+_b a_d a_c
    r=ann(st,c)
    if r is None: return None
    s1,st1=r
    r=ann(st1,d)
    if r is None: return None
    s2,st2=r
    r=cre(st2,b)
    if r is None: return None
    s3,st3=r
    r=cre(st3,a)
    if r is None: return None
    s4,st4=r
    return s1*s2*s3*s4,st4
Hc=np.zeros((D,D)); Hf=np.zeros((D,D))
for j,st in enumerate(dets):
    for a in range(N):
        for b in range(N):
            if orbs[a][1]!=orbs[b][1]: continue
            h=Wcf[ms.index(orbs[a][0]),ms.index(orbs[b][0])]
            if abs(h)>1e-12:
                r=op1(st,a,b)
                if r: Hf[idx[r[1]],j]+=h*r[0]
    for (a,b,c,d),v in Vt.items():
        r=op2(st,a,b,c,d)
        if r: Hc[idx[r[1]],j]+=0.5*v*r[0]
# S^2
Sm=np.zeros((D,D))
for j,st in enumerate(dets):
    for m in ms:
        r=op1(st,orbs.index((m,-1)),orbs.index((m,1)))  # a+_dn a_up  -> S-
        if r: Sm[idx[r[1]],j]+=r[0]
Sp=Sm.T
Sz=np.array([0.5*sum(1 if orbs[x][1]==1 else -1 for x in st) for st in dets])
S2=np.diag(Sz**2)+0.5*(Sp@Sm+Sm@Sp)
# Sz=5/2 sextet state check: all-up determinant
up=tuple(sorted(orbs.index((m,1)) for m in ms))
print("sextet diag Hc,Hf:",Hc[idx[up],idx[up]],Hf[idx[up],idx[up]])
# S=1/2 subspace
s2e,U=np.linalg.eigh(S2)
P=U[:,np.abs(s2e-0.75)<1e-6]; P5=U[:,np.abs(s2e-8.75)<1e-6]
print("dim S=1/2:",P.shape[1])
def doublet_ground(Dq):
    H=Hc+Dq*Hf
    return np.linalg.eigvalsh(P.T@H@P)[0]
def sextet_E(Dq):
    H=Hc+Dq*Hf
    return (P5.T@H@P5)[0,0] if P5.shape[1]==1 else np.linalg.eigvalsh(P5.T@H@P5)[0]
for Dq in [0,500,1000,1500,1700,1800,2000,2500,3000]:
    print(Dq, round(doublet_ground(Dq),1), round(sextet_E(Dq),1))
f=lambda Dq: doublet_ground(Dq)-sextet_E(Dq)
Dqc=brentq(f,0,5000)
print("crossover Dq =",Dqc, " Dq/B=",Dqc/B, " 10Dq=",10*Dqc)
