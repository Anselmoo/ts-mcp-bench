import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
from math import sqrt
l=2; ms=list(range(-2,3))
def Ck(k,q,m,mp):
    if abs(q)>k: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*wigner_3j(l,k,l,0,0,0)*(2*l+1))
def Acoef(k,m1,m2,m3,m4):
    return sum((-1)**q*Ck(k,q,m1,m3)*Ck(k,-q,m2,m4) for q in range(-k,k+1))
Vk={k:np.zeros((5,5,5,5)) for k in (0,2,4)}
for k in (0,2,4):
    for i1,m1 in enumerate(ms):
        for i2,m2 in enumerate(ms):
            for i3,m3 in enumerate(ms):
                for i4,m4 in enumerate(ms):
                    if m1+m2==m3+m4: Vk[k][i1,i2,i3,i4]=Acoef(k,m1,m2,m3,m4)
s2=sqrt(2)
U=np.zeros((5,5),dtype=complex)
idx={m:i for i,m in enumerate(ms)}
U[0,idx[0]]=1
U[1,idx[2]]=1/s2; U[1,idx[-2]]=1/s2
U[2,idx[2]]=1/(1j*s2); U[2,idx[-2]]=-1/(1j*s2)
U[3,idx[1]]=1/s2; U[3,idx[-1]]=-1/s2
U[4,idx[1]]=1/(1j*s2); U[4,idx[-1]]=1/(1j*s2)
Vr={k:np.einsum('aw,bx,cy,dz,wxyz->abcd',U.conj(),U.conj(),U,U,Vk[k]).real for k in Vk}
states=list(itertools.combinations(range(10),6))
sidx={s:i for i,s in enumerate(states)}
def apply_ops(ops,state):
    occ=list(state); sign=1
    for (p,dag) in reversed(ops):
        n=sum(1 for o in occ if o<p)
        if dag:
            if p in occ: return None,0
            sign*=(-1)**n; occ.append(p); occ.sort()
        else:
            if p not in occ: return None,0
            sign*=(-1)**n; occ.remove(p)
    return tuple(occ),sign
N=len(states)
quads=[(p,q,r,s) for p in range(10) for q in range(10) for r in range(10) for s in range(10) if p%2==r%2 and q%2==s%2]
two=[];one=[]
for j,st in enumerate(states):
    for (p,q,r,s) in quads:
        new,sg=apply_ops([(p,True),(q,True),(s,False),(r,False)],st)
        if new is not None: two.append((j,sidx[new],0.5*sg,(p//2,q//2,r//2,s//2)))
    for p in range(10):
        for q in range(10):
            if p%2!=q%2: continue
            new,sg=apply_ops([(p,True),(q,False)],st)
            if new is not None: one.append((j,sidx[new],sg,(p//2,q//2)))
S2=np.zeros((N,N))
for j,st in enumerate(states):
    Ms=sum(0.5 if p%2==0 else -0.5 for p in st); S2[j,j]+=Ms*Ms
    for o1 in range(5):
        for o2 in range(5):
            new,sg=apply_ops([(2*o1,True),(2*o1+1,False),(2*o2+1,True),(2*o2,False)],st)
            if new is not None: S2[sidx[new],j]+=sg
Ms0=[j for j,st in enumerate(states) if sum(0.5 if p%2==0 else -0.5 for p in st)==0]
w,v=np.linalg.eigh(S2[np.ix_(Ms0,Ms0)]); null=v[:,np.abs(w)<1e-8]
def levels(Dq,B,C):
    F4=C*441/35.0; F2=(B*441+5*F4)/9.0
    Vs=Vr[2]*F2+Vr[4]*F4
    h=np.diag([6*Dq,6*Dq,-4*Dq,-4*Dq,-4*Dq])
    H=np.zeros((N,N))
    for (j,i,sg,(a,b,c,d)) in two: H[i,j]+=sg*Vs[a,b,c,d]
    for (j,i,sg,(a,b)) in one: H[i,j]+=sg*h[a,b]
    return np.linalg.eigvalsh(null.T@H[np.ix_(Ms0,Ms0)]@null)
def T12(x):
    B=1000.
    e=levels(x*B,B,4.5*B); e=e-e[0]
    # first 3-fold triplet and second 3-fold triplet
    trip=[]
    i=1
    while i<len(e) and len(trip)<2:
        j=i
        while j+1<len(e) and abs(e[j+1]-e[i])<1.0: j+=1
        if j-i+1==3: trip.append(e[i]/1000.)
        i=j+1
    return trip
def ratio(x):
    t=T12(x); return t[1]/t[0]-25381/16474
xs=brentq(ratio,2.0,3.0,xtol=1e-7)
t=T12(xs); B=16474/t[0]*1000
print("Dq/B=",xs,"E1/B",t[0],"E2/B",t[1],"B=",B,"Dq=",xs*B,"C=",4.5*B)
# verify
e=levels(xs*B,B,4.5*B); e=e-e[0]
print("check: E(1T1)=",t[0]*B," E(1T2)=",t[1]*B)
