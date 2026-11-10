import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2; ms=list(range(-l,l+1))
def red(k): return float((-1)**l*(2*l+1)*wigner_3j(l,k,l,0,0,0))
def Cmat(k,q):
    M=np.zeros((5,5))
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            if -m+q+mp!=0 or abs(q)>k: continue
            M[i,j]=float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp))*red(k)
    return M
M4={q:Cmat(4,q) for q in range(-4,5)}
Mcub=M4[0]+np.sqrt(5/14)*(M4[4]+M4[-4])
Hcub=21.0*Mcub
def so(s,mi): return s*5+mi
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(10),5)]
didx={d:i for i,d in enumerate(dets)}; N=len(dets)
def op(kind,i,s):
    out={}
    for dd,amp in s.items():
        if kind=='a':
            if not (dd>>i)&1: continue
            sg=(-1)**bin(dd&((1<<i)-1)).count('1'); nd=dd^(1<<i)
        else:
            if (dd>>i)&1: continue
            sg=(-1)**bin(dd&((1<<i)-1)).count('1'); nd=dd|(1<<i)
        out[nd]=out.get(nd,0)+amp*sg
    return out
def one_body(Mat):
    Mx=np.zeros((N,N))
    for a in range(10):
        for c in range(10):
            sa,ma=divmod(a,5); sc,mc=divmod(c,5)
            if sa!=sc or abs(Mat[ma,mc])<1e-12: continue
            for j,dd in enumerate(dets):
                s=op('a',c,{dd:1.0}); s=op('c',a,s)
                for nd,amp in s.items(): Mx[didx[nd],j]+=Mat[ma,mc]*amp
    return Mx
def twobody(k):
    Mx=np.zeros((N,N))
    for a,b,c,d in itertools.product(range(10),repeat=4):
        sa,ma=divmod(a,5); sb,mb=divmod(b,5); sc,mc=divmod(c,5); sd,md=divmod(d,5)
        if sa!=sc or sb!=sd: continue
        val=sum((-1)**q*Cmat(k,q)[ma,mc]*Cmat(k,-q)[mb,md] for q in range(-k,k+1))
        if abs(val)<1e-12: continue
        for j,dd in enumerate(dets):
            s=op('a',c,{dd:1.0}); s=op('a',d,s); s=op('c',b,s); s=op('c',a,s)
            for nd,amp in s.items(): Mx[didx[nd],j]+=0.5*val*amp
    return Mx
V2=twobody(2); V4=twobody(4)
Hcf=one_body(Hcub)
Sp=np.zeros((N,N))
for m in range(5):
    for j,dd in enumerate(dets):
        s=op('a',so(1,m),{dd:1.0}); s=op('c',so(0,m),s)
        for nd,amp in s.items(): Sp[didx[nd],j]+=amp
Szd=np.diag([(sum(1 for i in range(5) if (dd>>i)&1)-sum(1 for i in range(5,10) if (dd>>i)&1))/2 for dd in dets])
S2=Sp.T@Sp+Szd@Szd+Szd
ms32=[i for i,dd in enumerate(dets) if abs(Szd[i,i]-1.5)<1e-9]
w,v=np.linalg.eigh(S2[np.ix_(ms32,ms32)])
Q=v[:,np.abs(w-3.75)<1e-6]
i52=[i for i,dd in enumerate(dets) if abs(Szd[i,i]-2.5)<1e-9][0]
def energies(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    H=Dq*Hcf+F2*V2+F4*V4
    E6=H[i52,i52]
    Hq=Q.T@H[np.ix_(ms32,ms32)]@Q
    return np.sort(np.linalg.eigvalsh(Hq))-E6
def levels(s):
    lv=[]
    for e in s:
        if not lv or abs(e-lv[-1][0])>1e-2: lv.append([e,1])
        else: lv[-1][1]+=1
    return lv
print('check eg/t2g via H at Dq=1, B=C=0 sextet:', energies(1000,0,0)[:3])
for Dq,B,C in [(1000,800,3200),(2000,600,2400)]:
    print(Dq,B,C,[(round(e,1),n) for e,n in levels(energies(Dq,B,C))][:8])
obs=[19180,22130,23370]
def res(p):
    Dq,B,C=p
    lv=levels(energies(Dq,B,C))
    # ordered distinct levels; take lowest three: T1(3), T2(3), E(2) pattern with ordering
    return [lv[0][0]-obs[0], lv[1][0]-obs[1], lv[2][0]-obs[2]]
sol=least_squares(res,[2000,700,3000])
print(sol.x, res(sol.x))
print([(round(e,1),n) for e,n in levels(energies(*sol.x))][:10])
