import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=621.,2851.
F4=C/35; F2=B+5*F4
Fk={2:F2*49,4:F4*441}
cache={}
def c(k,m1,m2):
    key=(k,m1,m2)
    if key not in cache:
        cache[key]=float(gaunt(2,k,2,-m1,m1-m2,m2)*(-1)**m1*np.sqrt(4*np.pi/(2*k+1)))
    return cache[key]
def eri(a,b,cc,d):
    if a[1]!=cc[1] or b[1]!=d[1] or a[0]+b[0]!=cc[0]+d[0]: return 0
    return sum(c(k,a[0],cc[0])*c(k,d[0],b[0])*Fk[k] for k in (2,4))
so=[(m,s) for m in range(-2,3) for s in (1,-1)]
def Voct(Dq):
    M=np.zeros((5,5));M[2,2]=6*Dq;M[1,1]=M[3,3]=-4*Dq;M[0,0]=M[4,4]=Dq;M[0,4]=M[4,0]=5*Dq;return M
def build(dets,Dq):
    N=len(dets);H=np.zeros((N,N));Vm=Voct(Dq)
    for i,d in enumerate(dets):
        for j in range(i,N):
            e=dets[j]
            d1=[x for x in d if x not in e]; d2=[x for x in e if x not in d]
            if len(d1)>2: continue
            val=0
            if not d1:
                for p in d: val+=Vm[so[p][0]+2,so[p][0]+2]
                for a in range(5):
                    for b in range(a+1,5):
                        p,q=so[d[a]],so[d[b]];val+=eri(p,q,p,q)-eri(p,q,q,p)
            else:
                rep=list(d)
                for x,y in zip(d1,d2): rep[rep.index(x)]=y
                par=sum(1 for a in range(5) for b in range(a+1,5) if rep[a]>rep[b])
                if len(d1)==1:
                    p,q=so[d1[0]],so[d2[0]]
                    if p[1]==q[1]: val+=Vm[p[0]+2,q[0]+2]
                    for r in d:
                        if r!=d1[0]: rr=so[r];val+=eri(p,rr,q,rr)-eri(p,rr,rr,q)
                else:
                    p1,p2=so[d1[0]],so[d1[1]];q1,q2=so[d2[0]],so[d2[1]]
                    val+=eri(p1,p2,q1,q2)-eri(p1,p2,q2,q1)
                val*=(-1)**par
            H[i,j]=H[j,i]=val
    return H
alld=list(itertools.combinations(range(10),5))
Ms=lambda d: sum(so[p][1] for p in d)/2
D5=[d for d in alld if Ms(d)==2.5]; D05=[d for d in alld if Ms(d)==0.5]; D15=[d for d in alld if Ms(d)==1.5]
def f(Dq):
    e6=np.linalg.eigvalsh(build(D5,Dq))[0]
    e4=np.linalg.eigvalsh(build(D15,Dq))
    e2=np.linalg.eigvalsh(build(D05,Dq))
    # remove sextet component: drop one eigenvalue closest to e6
    k=np.argmin(abs(e2-e6)); e2=np.delete(e2,k)
    k4=np.argmin(abs(e4-e6)); e4=np.delete(e4,k4)
    return min(e2.min(),e4.min())-e6, e4.min()-e6
for D in [1500,1700,1800,1900]: print(D,f(D))
x=brentq(lambda D:f(D)[0],1500,2000,xtol=1e-4);print(x)
