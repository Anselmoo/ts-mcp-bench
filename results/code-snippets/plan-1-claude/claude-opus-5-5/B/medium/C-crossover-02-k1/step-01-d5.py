import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=621.,2851.
F4=C/35; F2=B+5*F4; F0=0
Fk={0:0,2:F2*49,4:F4*441}
ml=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) for l=2
    return float(gaunt(2,k,2,-m1,m1-m2,m2)*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5)
# check normalisation: c^k(lm,l'm') = sqrt(4pi/(2k+1)) * int Y*lm Ykq Yl'm'
cache={}
def c(k,a,b):
    if (k,a,b) not in cache: cache[(k,a,b)]=ck(k,a,b)
    return cache[(k,a,b)]
def eri(a,b,cc,d): # <ab|1/r|cd>, orbitals (m,s)
    if a[1]!=cc[1] or b[1]!=d[1]: return 0
    if a[0]+b[0]!=cc[0]+d[0]: return 0
    return sum(c(k,a[0],cc[0])*c(k,d[0],b[0])*Fk[k] for k in (2,4))
so=[(m,s) for m in ml for s in (1,-1)]
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
# octahedral one-electron in real basis -> complex: Dq*(6 for eg, -4 t2); V4 operator: <m|V|m'>
V=np.zeros((5,5))
# standard: <0|V|0>=6Dq, <±1|V|±1>=-4Dq, <±2|V|±2>=Dq, <2|V|-2>=5Dq
def Voct(Dq):
    M=np.zeros((5,5));d={-2:0,-1:1,0:2,1:3,2:4}
    M[2,2]=6*Dq;M[1,1]=M[3,3]=-4*Dq;M[0,0]=M[4,4]=Dq;M[0,4]=M[4,0]=5*Dq
    return M
def build(Dq):
    H=np.zeros((N,N));Vm=Voct(Dq)
    for i,d in enumerate(dets):
        for j,e in enumerate(dets):
            if j<i: continue
            diff1=[x for x in d if x not in e]; diff2=[x for x in e if x not in d]
            if len(diff1)>2: continue
            val=0
            def sign(det,p,q):
                # bring p to front order... use generic: replace
                pass
            if len(diff1)==0:
                for p in d: val+=Vm[so[p][0]+2,so[p][0]+2]
                for a in range(5):
                    for b in range(a+1,5):
                        p,q=so[d[a]],so[d[b]]
                        val+=eri(p,q,p,q)-eri(p,q,q,p)
            else:
                # compute phase by permutation
                ld=list(d); 
                # replace diff1 with diff2 in place, sort, count parity
                rep=ld[:]
                for x,y in zip(diff1,diff2): rep[rep.index(x)]=y
                perm=np.argsort(rep); 
                # parity of sorting rep
                par=0;r=rep[:]
                for a in range(len(r)):
                    for b in range(a+1,len(r)):
                        if r[a]>r[b]: par+=1
                ph=(-1)**par
                if len(diff1)==1:
                    p,q=so[diff1[0]],so[diff2[0]]
                    if p[1]==q[1]: val+=Vm[p[0]+2,q[0]+2]
                    for r_ in d:
                        if r_==diff1[0]: continue
                        rr=so[r_]
                        val+=eri(p,rr,q,rr)-eri(p,rr,rr,q)
                else:
                    p1,p2=so[diff1[0]],so[diff1[1]];q1,q2=so[diff2[0]],so[diff2[1]]
                    val+=eri(p1,p2,q1,q2)-eri(p1,p2,q2,q1)
                val*=ph
            H[i,j]=val;H[j,i]=val
    return H
Ms=np.array([sum(so[p][1] for p in d)/2 for d in dets])
def gap(Dq):
    H=build(Dq)
    s5=Ms==2.5; s05=Ms==0.5; s15=Ms==1.5
    e6=np.linalg.eigvalsh(H[np.ix_(s5,s5)])[0]
    e2=np.linalg.eigvalsh(H[np.ix_(s05,s05)])[0]
    return e6,e2
for Dq in [0,1000,1500,2000]:
    print(Dq,gap(Dq))
f=lambda Dq: (lambda a:a[1]-a[0])(gap(Dq))
print(brentq(f,1000,3000,xtol=1e-6))
