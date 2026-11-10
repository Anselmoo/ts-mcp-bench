cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):  # <2m1|C^k|2m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*25/25*gaunt(2,k,2,-m1,q,m2)*1)
# check normalization: c^k(lm,l'm') = (-1)^m sqrt(4pi/(2k+1)) * gaunt(l,k,l',-m,q,m')
C={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def V(m):
    return 0
def H(Dq,B,Cr):
    F={2:49*B+7*Cr,4:63*Cr/5}
    cf=np.zeros((5,5))
    for i,m in enumerate(ms):
        cf[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    cf[0,4]=cf[4,0]=5*Dq
    def g(a,b,c,d): # <ab|1/r|cd> spin orbitals
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
        return sum(F[k]*C[(k,ma,mc)]*C[(k,md,mb)] for k in (2,4))
    N=len(dets);Hm=np.zeros((N,N))
    for d in dets:
        I=idx[d]
        # one-body
        for p,a in enumerate(d):
            for b in range(10):
                if so[a][1]!=so[b][1]: continue
                v=cf[ms.index(so[b][0]),ms.index(so[a][0])]
                if v==0: continue
                if b!=a and b in d: continue
                new=list(d);new[p]=b
                sign=1
                # sort with sign
                arr=new[:]
                for i in range(len(arr)):
                    for j in range(len(arr)-1-i):
                        if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j];sign=-sign
                Hm[idx[tuple(arr)],I]+=sign*v
        # two-body: sum over pairs
        for (p,q) in itertools.combinations(range(3),2):
            a,b=d[p],d[q]
            for c in range(10):
                for e in range(10):
                    if c==e: continue
                    rest=[x for k,x in enumerate(d) if k not in (p,q)]
                    if c in rest or e in rest: continue
                    v=g(c,e,a,b)-g(e,c,a,b)
                    if v==0: continue
                    new=list(d);new[p]=c;new[q]=e
                    sign=1;arr=new[:]
                    for i in range(3):
                        for j in range(2-i):
                            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j];sign=-sign
                    if c<e or True:
                        Hm[idx[tuple(arr)],I]+=0.5*sign*v
    return Hm
def levels(Dq,B,Cr):
    e=np.linalg.eigvalsh(H(Dq,B,Cr)); e=e-e[0]
    u=[]
    for x in e:
        if not u or x-u[-1][0]>1e-3: u.append([x,1])
        else: u[-1][1]+=1
    return u
print(levels(0,1000,4000)[:6])  # free ion check: 4F, 4P=15B, 2G=4B+3C...
L=levels(2155,657.4,4*657.4)
for x in L[:8]: print(x)
EOF
python3 /tmp/d3.py