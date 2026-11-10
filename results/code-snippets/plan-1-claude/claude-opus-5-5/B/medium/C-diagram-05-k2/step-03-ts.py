import numpy as np, itertools, json
from sympy.physics.wigner import gaunt
B=859.;C=3660.
F2=49*B+7*C; F4=441*C/35
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # c^k(l m1, l m2) = <2m1|C^k_{m1-m2}|2m2>
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
Fk={2:F2,4:F4}
def U(a,b,c,d): # <ab|1/r|cd>, orbitals m; spin handled outside
    if a+b!=c+d: return 0.
    return sum(Fk[k]*CK[(k,a,c)]*CK[(k,d,b)] for k in (2,4))
so=[(m,s) for m in ms for s in (1,-1)]
dets=list(itertools.combinations(range(10),7)); idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply2(det,p,q,r,s):  # a+_p a+_q a_s a_r |det>
    st=list(det); sign=1
    for o in (r,s):
        if o not in st: return None,0
        i=st.index(o); sign*= (-1)**i; st.pop(i)
    for o in (q,p):
        if o in st: return None,0
        i=sum(1 for x in st if x<o); sign*=(-1)**i; st.insert(i,o)
    return tuple(st),sign
Hee=np.zeros((N,N))
for j,d in enumerate(dets):
    for p in range(10):
      for q in range(10):
        for r in range(10):
          for s in range(10):
            if so[p][1]!=so[r][1] or so[q][1]!=so[s][1]: continue
            v=U(so[p][0],so[q][0],so[r][0],so[s][0])
            if v==0: continue
            nd,sg=apply2(d,p,q,r,s)
            if nd is None: continue
            Hee[idx[nd],j]+=0.5*v*sg
Vm=np.zeros((5,5)); 
for m,v in zip(ms,[1,-4,6,-4,1]): Vm[m+2,m+2]=v
Vm[0,4]=Vm[4,0]=5
Hcf=np.zeros((N,N))
for j,d in enumerate(dets):
    for p in d:
        for r in range(10):
            if so[p][1]!=so[r][1]: continue
            v=Vm[so[r][0]+2,so[p][0]+2]
            if v==0: continue
            st=list(d); i=st.index(p); sg=(-1)**i; st.pop(i)
            if r in st: continue
            k=sum(1 for x in st if x<r); sg*=(-1)**k; st.insert(k,r)
            Hcf[idx[tuple(st)],j]+=v*sg
# S^2
S2=np.zeros((N,N))
for j,d in enumerate(dets):
    Sz=sum(so[p][1] for p in d)/2; S2[j,j]+=Sz*Sz+Sz
    # S- S+ : S+ raises down->up
    for p in d:
        if so[p][1]==-1:
            r=p-1  # up orbital same m
            st=list(d); i=st.index(p); sg=(-1)**i; st.pop(i)
            if r in st: continue
            k=sum(1 for x in st if x<r); sg*=(-1)**k; st.insert(k,r)
            # now apply S- to all
            for p2 in st:
                if so[p2][1]==1:
                    r2=p2+1; st2=list(st); i2=st2.index(p2); sg2=sg*(-1)**i2; st2.pop(i2)
                    if r2 in st2: continue
                    k2=sum(1 for x in st2 if x<r2); sg2*=(-1)**k2; st2.insert(k2,r2)
                    S2[idx[tuple(st2)],j]+=sg2
ML=np.array([sum(so[p][0] for p in d) for d in dets])
C4=np.diag(np.exp(-1j*np.pi/2*ML))
# L^2 for free ion labels
L2=np.zeros((N,N))
def lp(m): return np.sqrt(6-m*(m+1))
for j,d in enumerate(dets):
    L2[j,j]+=ML[j]**2+ML[j]
    for p in d:
        m,s=so[p]
        if m==2: continue
        r=so.index((m+1,s)); st=list(d); i=st.index(p); sg=(-1)**i*lp(m); st.pop(i)
        if r in st: continue
        k=sum(1 for x in st if x<r); sg*=(-1)**k; st.insert(k,r)
        for p2 in st:
            m2,s2=so[p2]
            if m2==-2: continue
            r2=so.index((m2-1,s2)); st2=list(st); i2=st2.index(p2); sg2=sg*(-1)**i2*lp(m2-1); st2.pop(i2)
            if r2 in st2: continue
            k2=sum(1 for x in st2 if x<r2); sg2*=(-1)**k2; st2.insert(k2,r2)
            L2[idx[tuple(st2)],j]+=sg2
np.save('H.npy',np.array([Hee,Hcf,S2,L2])); np.save('ML.npy',ML)
