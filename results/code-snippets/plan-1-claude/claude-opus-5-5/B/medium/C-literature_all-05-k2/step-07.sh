python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def srt(arr):
    arr=arr[:];sign=1
    for i in range(len(arr)):
        for j in range(len(arr)-1-i):
            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j];sign=-sign
    return tuple(arr),sign
def H(Dq,B,Cr):
    F={2:49*B+7*Cr,4:63*Cr/5}
    cf=np.zeros((5,5))
    for i,m in enumerate(ms): cf[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    cf[0,4]=cf[4,0]=5*Dq
    def g(a,b,c,d):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
        return sum(F[k]*C[(k,ma,mc)]*C[(k,md,mb)] for k in (2,4))
    N=len(dets);Hm=np.zeros((N,N))
    for d in dets:
        I=idx[d]
        for p,a in enumerate(d):
            for b in range(10):
                if so[a][1]!=so[b][1]: continue
                v=cf[ms.index(so[b][0]),ms.index(so[a][0])]
                if v==0 or (b!=a and b in d): continue
                new=list(d);new[p]=b;t,s=srt(new);Hm[idx[t],I]+=s*v
        for (p,q) in itertools.combinations(range(3),2):
            a,b=d[p],d[q];rest=[x for k,x in enumerate(d) if k not in (p,q)]
            for c in range(10):
                for e in range(10):
                    if c==e or c in rest or e in rest: continue
                    v=g(c,e,a,b)-g(e,c,a,b)
                    if v==0: continue
                    new=list(d);new[p]=c;new[q]=e;t,s=srt(new);Hm[idx[t],I]+=0.5*s*v
    return Hm
def levels(Dq,B,Cr):
    e=np.linalg.eigvalsh(H(Dq,B,Cr)); e=e-e[0];u=[]
    for x in e:
        if not u or x-u[-1][0]>1e-3: u.append([round(float(x),1),1])
        else: u[-1][1]+=1
    return u
for Cr in [3398,3400]:
    print(Cr,levels(2155,657.4,Cr)[:12])
EOF