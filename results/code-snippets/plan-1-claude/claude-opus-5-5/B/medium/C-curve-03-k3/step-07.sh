cd $TMPDIR && cat << 'EOF' > d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=784.;C=3699.
F2=49*(B+C/7); F4=441*C/35
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
def R(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return F2*CK[(2,m1,m3)]*CK[(2,m4,m2)]+F4*CK[(4,m1,m3)]*CK[(4,m4,m2)]
so=[(m,s) for m in ms for s in (1,-1)]
states=list(itertools.combinations(range(10),7))
idx={s:i for i,s in enumerate(states)}
N=len(states)
def ann(l,o):
    if o not in l: return None,0
    i=l.index(o); return l[:i]+l[i+1:], (-1)**i
def cre(l,o):
    if o in l: return None,0
    l2=sorted(l+[o]); return l2,(-1)**l2.index(o)
def apply2(st,p,q,r,s_):
    l=list(st); sign=1
    for f,o in ((ann,s_),(ann,r),(cre,q),(cre,p)):
        l,sg=f(l,o)
        if l is None: return None,0
        sign*=sg
    return tuple(l),sign
H0=np.zeros((N,N))
for j,st in enumerate(states):
    for p in range(10):
     for q in range(10):
      for r in range(10):
       for s_ in range(10):
        if so[p][1]!=so[r][1] or so[q][1]!=so[s_][1]: continue
        v=R(so[p][0],so[q][0],so[r][0],so[s_][0])
        if v==0: continue
        res,sg=apply2(st,p,q,r,s_)
        if res is None: continue
        H0[idx[res],j]+=0.5*v*sg
V1=np.zeros((5,5));
d={-2:1,-1:-4,0:6,1:-4,2:1}
for i,m in enumerate(ms): V1[i,i]=d[m]
V1[0,4]=V1[4,0]=5
def onebody(M):
    O=np.zeros((N,N))
    for j,st in enumerate(states):
        for p in range(10):
            for r in range(10):
                if so[p][1]!=so[r][1]: continue
                v=M[ms.index(so[p][0]),ms.index(so[r][0])]
                if v==0: continue
                l,s1=ann(list(st),r)
                if l is None: continue
                l,s2=cre(l,p)
                if l is None: continue
                O[idx[tuple(l)],j]+=v*s1*s2
    return O
HV=onebody(V1)
c4=np.array([np.prod([np.exp(-1j*so[o][0]*np.pi/2) for o in st]) for st in states])
Sz=np.array([sum(so[o][1] for o in st)/2 for st in states])
Sp=np.zeros((N,N))
for j,st in enumerate(states):
    for o in st:
        if so[o][1]==-1:
            p=so.index((so[o][0],1))
            l,s1=ann(list(st),o)
            l,s2=cre(l,p)
            if l is None: continue
            Sp[idx[tuple(l)],j]+=s1*s2
S2=Sp.T@Sp+np.diag(Sz**2-Sz)
lab={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}
for x in (0,1.45,2.45,3.0):
    H=H0+x*B*HV
    w,U=np.linalg.eigh(H)
    groups=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<1e-4: j+=1
        groups.append((i,j)); i=j
    out=[]
    for (i,j) in groups[:6]:
        P=U[:,i:j]
        s2=np.trace(P.T@S2@P)/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        mult=int(round(2*S+1)); deg=(j-i)//mult
        ch=np.trace(P.conj().T@(c4[:,None]*P)).real/mult
        out.append((f"{mult}{lab.get((deg,int(round(ch))),'?')}",round((w[i]-w[0])/B,3)))
    print(x,out)
EOF
python3 d7.py