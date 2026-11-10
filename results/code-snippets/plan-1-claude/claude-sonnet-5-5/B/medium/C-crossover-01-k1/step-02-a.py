import numpy as np, itertools, sympy
from sympy.physics.wigner import gaunt as G
from scipy.optimize import brentq
B=706.;C=2734.
F4=C/35;F2=B+5*F4;Fk={2:F2,4:F4}
def a(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float((-1)**m*G(2,k,2,-m,q,mp)*sympy.sqrt(sympy.Rational(4)*sympy.pi/(2*k+1)))
A={(k,m,mp):a(k,m,mp) for k in (2,4) for m in range(-2,3) for mp in range(-2,3)}
so=[(m,s) for m in range(-2,3) for s in (1,-1)]
def Vee(p,q,r,s):  # <pq|g|rs>
    if p[1]!=r[1] or q[1]!=s[1] or p[0]+q[0]!=r[0]+s[0]: return 0.
    return sum(Fk[k]*A[(k,p[0],r[0])]*A[(k,s[0],q[0])] for k in (2,4))
def ham(ms,Dq):
    dets=[d for d in itertools.combinations(range(10),4) if sum(so[i][1] for i in d)==ms]
    idx={d:i for i,d in enumerate(dets)};n=len(dets);H=np.zeros((n,n))
    h=np.zeros((5,5));
    for m,v in zip(range(-2,3),[1,-4,6,-4,1]):h[m+2,m+2]=v*Dq
    h[0,4]=h[4,0]=5*Dq
    def h1(i,j):
        return h[so[i][0]+2,so[j][0]+2] if so[i][1]==so[j][1] else 0
    for I,d in enumerate(dets):
        for J,e in enumerate(dets):
            # one-body
            diff=set(d)^set(e)
            val=0
            if len(diff)==0:
                val+=sum(h1(i,i) for i in d)
                for i,j in itertools.combinations(d,2):
                    val+=Vee(so[i],so[j],so[i],so[j])-Vee(so[i],so[j],so[j],so[i])
            elif len(diff)==2:
                i=list(set(d)-set(e))[0];j=list(set(e)-set(d))[0]
                # sign
                def sgn(d,o,new):
                    l=list(d);p=l.index(o);l[p]=new;
                    s=1
                    # sort l with parity
                    perm=sorted(range(4),key=lambda x:l[x])
                    # parity of perm
                    par=0;pp=perm[:]
                    for x in range(4):
                        while pp[x]!=x:
                            y=pp[x];pp[x],pp[y]=pp[y],pp[x];par+=1
                    return (-1)**par
                sg=sgn(d,i,j)
                val+=h1(i,j)
                for k in d:
                    if k==i:continue
                    val+=Vee(so[i],so[k],so[j],so[k])-Vee(so[i],so[k],so[k],so[j]) if False else 0
                    val+=Vee(so[j],so[k],so[i],so[k])-Vee(so[j],so[k],so[k],so[i])
                val*=sg
            elif len(diff)==4:
                i1,i2=sorted(set(d)-set(e));j1,j2=sorted(set(e)-set(d))
                # d -> e: remove i1,i2 add j1,j2 ; sign
                def sg2():
                    l=list(d);l[l.index(i1)]=j1;l[l.index(i2)]=j2
                    perm=sorted(range(4),key=lambda x:l[x]);par=0;pp=perm[:]
                    for x in range(4):
                        while pp[x]!=x:
                            y=pp[x];pp[x],pp[y]=pp[y],pp[x];par+=1
                    return (-1)**par
                val=sg2()*(Vee(so[j1],so[j2],so[i1],so[i2])-Vee(so[j1],so[j2],so[i2],so[i1]))
            H[I,J]=val
    return np.linalg.eigvalsh((H+H.T)/2)
def gap(Dq):
    q=ham(2,Dq);t=ham(1,Dq)
    t=list(t)
    for x in q:
        j=min(range(len(t)),key=lambda k:abs(t[k]-x));t.pop(j)
    return q[0]-t[0]
for D in (1000,1500,2000,2500):print(D,gap(D))
print(brentq(gap,1000,3000))
