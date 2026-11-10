
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (0.5,-0.5)]
def ck(k,m1,m2):
    return float((-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2)*np.sqrt(4*np.pi/(2*k+1)))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml}
def g(a,b,c,d,F):
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]: return 0
    return sum(F[k]*CK[(k,a[0],c[0])]*CK[(k,d[0],b[0])] for k in (0,2,4))
def Vcf(Dq):
    V=np.zeros((5,5)); i={m:k for k,m in enumerate(ml)}
    V[i[0],i[0]]=6*Dq; V[i[1],i[1]]=V[i[-1],i[-1]]=-4*Dq
    V[i[2],i[2]]=V[i[-2],i[-2]]=Dq; V[i[2],i[-2]]=V[i[-2],i[2]]=5*Dq
    return V
dets=list(itertools.combinations(range(10),3)); idx={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    st=list(det); sign=1
    for dag,o in reversed(ops):
        if dag:
            if o in st: return None,0
            pos=sum(1 for x in st if x<o); sign*=(-1)**pos; st.insert(pos,o)
        else:
            if o not in st: return None,0
            pos=st.index(o); sign*=(-1)**pos; st.pop(pos)
    return tuple(st),sign
n=len(dets)
def build(F,V):
    Hm=np.zeros((n,n))
    for J,e in enumerate(dets):
        for p in range(10):
            for q in e:
                a,b=so[p],so[q]
                h=V[ml.index(a[0]),ml.index(b[0])] if a[1]==b[1] else 0
                if h:
                    r,s=apply([(1,p),(0,q)],e)
                    if r: Hm[idx[r],J]+=h*s
        for p in range(10):
         for q in range(10):
          for r_ in e:
           for s_ in e:
            v=g(so[p],so[q],so[r_],so[s_],F)
            if v:
                r,s=apply([(1,p),(1,q),(0,s_),(0,r_)],e)
                if r: Hm[idx[r],J]+=0.5*v*s
    return Hm
Z=np.zeros((5,5))
HB=build({0:0,2:49,4:0},Z); HC=build({0:0,2:7,4:441/35},Z); HD=build({0:0,2:0,4:0},Vcf(1))
def levels(Dq,B,C):
    w=np.linalg.eigvalsh(Dq*HD+B*HB+C*HC); w=w-w[0]
    u=[]
    for x in w:
        if not u or x-u[-1][0]>1e-3: u.append([x,1])
        else: u[-1][1]+=1
    return u
print([(round(a,1),b) for a,b in levels(0,1000,4000)][:6])
print([(round(a,1),b) for a,b in levels(1750,610.9,4*610.9)][:6])
from scipy.optimize import fsolve
def res(p):
    Dq,B,C=p; L=levels(Dq,B,C)
    E2=[a for a,b in L if b==4][1]; Q=[a for a,b in L if b==12]
    return [Q[0]-17500,Q[1]-23800,E2-14300]
s=fsolve(res,[1750,610,2500]); print(s, s[2]/s[1]); print([(round(a,1),b) for a,b in levels(*s)][:6])
EOF
