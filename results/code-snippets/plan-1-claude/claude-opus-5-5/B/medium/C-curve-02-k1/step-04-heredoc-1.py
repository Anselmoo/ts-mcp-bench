import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=722.;C=3003.
F={0:0.,2:49*B+7*C,4:441*C/35}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    return float((-1)**(-m1)*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def g(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return sum(CK[(k,m1,m3)]*CK[(k,m4,m2)]*F[k] for k in (0,2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def crys(Dq):
    H=np.zeros((N,N));d={0:6,1:-4,-1:-4,2:1,-2:1}
    for a,dd in enumerate(dets):
        H[a,a]=sum(d[so[x][0]] for x in dd)*Dq
        for p in dd:
            m,s=so[p]
            if abs(m)==2:
                q=so.index((-m,s))
                if q in dd: continue
                st=list(dd);i=st.index(p);sign=(-1)**i;st.pop(i)
                j=sum(1 for y in st if y<q);sign*=(-1)**j;st.insert(j,q)
                H[idx[tuple(st)],a]+=sign*5*Dq
    return H
Hee=np.zeros((N,N))
for a,d in enumerate(dets):
    for p,q in itertools.combinations(d,2):
        rest=[x for x in d if x not in (p,q)]
        for r in range(10):
            for s_ in range(10):
                if r==s_ or r in rest or s_ in rest: continue
                (m1,s1),(m2,s2)=so[r],so[s_];(m3,s3),(m4,s4)=so[p],so[q]
                if s1!=s3 or s2!=s4: continue
                val=g(m1,m2,m3,m4)
                if val==0: continue
                st=list(d);sign=1
                for x in (p,q):
                    i=st.index(x);sign*=(-1)**i;st.pop(i)
                for x in (s_,r):
                    i=sum(1 for y in st if y<x);sign*=(-1)**i;st.insert(i,x)
                Hee[idx[tuple(st)],a]+=sign*val
Sz=np.zeros(N);Sp=np.zeros((N,N));R=np.zeros((N,N),complex)
for a,d in enumerate(dets):
    Sz[a]=sum(0.5 if so[x][1]==1 else -0.5 for x in d)
    R[a,a]=np.exp(1j*np.pi/2*sum(so[x][0] for x in d))
    for p in d:
        if so[p][1]==0:
            q=p+1
            if q in d: continue
            st=list(d);i=st.index(p);sign=(-1)**i;st.pop(i)
            j=sum(1 for y in st if y<q);sign*=(-1)**j;st.insert(j,q)
            Sp[idx[tuple(st)],a]+=sign
S2=Sp.T@Sp+np.diag(Sz**2+Sz)
w=np.linalg.eigvalsh(Hee);print(np.unique(np.round((w-w[0])/B,3)))
for Dq_B in (0.0,1.0,2.2,3.5):
    H=Hee+crys(Dq_B*B)+1e-6*S2
    w,v=np.linalg.eigh(H);E=(w-w[0])/B
    groups=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(E[j]-E[i])<1e-4: j+=1
        V=v[:,i:j];s2=np.trace(V.T@S2@V)/(j-i);S=(-1+np.sqrt(1+4*s2))/2
        mult=int(round(2*S+1));dim=(j-i)//mult
        ch=np.trace(V.conj().T@R@V).real/mult
        lab={1:'A1' if ch>0 else 'A2',2:'E',3:'T1' if ch>0 else 'T2'}.get(dim,str(dim))
        groups.append((round(E[i],4),f'{mult}{lab}'));i=j
    print(Dq_B,groups[:6])
