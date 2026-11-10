
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=722.;C=3003.
F2=49*(B+C/7);F4=441*(C/35)
def ck(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (1,-1)]
n=10
U=np.zeros((n,n,n,n))
for a,b,c,d in itertools.product(range(n),repeat=4):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[orbs[i] for i in (a,b,c,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    U[a,b,c,d]=sum(F*ck(k,ma,mc)*ck(k,md,mb) for k,F in ((2,F2),(4,F4)))
def cf(Dq):
    h=np.zeros((n,n))
    for i,(m,s) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            if s!=s2: continue
            if m==m2: h[i,j]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
            if abs(m)==2 and m2==-m: h[i,j]=5*Dq
    return h
dets=[d for d in itertools.combinations(range(n),3) if sum(orbs[i][1] for i in d)==1]
idx={d:i for i,d in enumerate(dets)}
def sign_sort(l):
    l=list(l);s=1
    for i in range(len(l)):
        for j in range(len(l)-1-i):
            if l[j]>l[j+1]: l[j],l[j+1]=l[j+1],l[j]; s=-s
    return s,tuple(l)
D=len(dets)
def H(Dq):
    h1=cf(Dq);Hm=np.zeros((D,D))
    for I,d in enumerate(dets):
        for p,i in enumerate(d):
            for j in range(n):
                if h1[j,i]==0: continue
                if j!=i and j in d: continue
                nd=list(d);nd[p]=j;s,t=sign_sort(nd)
                Hm[idx[t],I]+=s*h1[j,i]
        for p,q in itertools.combinations(range(3),2):
            i,j=d[p],d[q]
            rest=[x for r,x in enumerate(d) if r not in (p,q)]
            for k in range(n):
                for l in range(n):
                    if k==l or k in rest or l in rest: continue
                    v=U[k,l,i,j]
                    if v==0: continue
                    nd=list(d);nd[p]=k;nd[q]=l;s,t=sign_sort(nd)
                    Hm[idx[t],I]+=s*v
    return Hm
def c4(d): return np.prod([np.exp(-1j*orbs[i][0]*np.pi/2) for i in d])
C4=np.diag([c4(d) for d in dets])
S2=np.zeros((D,D))
for I,d in enumerate(dets):
    S2[I,I]+=0.75
    for p,i in enumerate(d):
        if orbs[i][1]!=-1: continue
        j=orbs.index((orbs[i][0],1))
        if j in d: continue
        nd=list(d);nd[p]=j
        for p2,i2 in enumerate(nd):
            if orbs[i2][1]!=1: continue
            j2=orbs.index((orbs[i2][0],-1))
            if j2 in nd: continue
            nd2=list(nd);nd2[p2]=j2;s,t=sign_sort(nd2)
            S2[idx[t],I]+=s
w0,_=np.linalg.eigh(H(0)); print(sorted(set(np.round((w0-w0[0])/B,3))))
for Dq in (1.0,2.2,3.5):
    w,v=np.linalg.eigh(H(Dq*B))
    w=w/B; groups=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-6: j+=1
        V=v[:,i:j];S=np.trace(V.T@S2@V)/(j-i);ch=np.trace(V.conj().T@C4@V).real
        groups.append((w[i],j-i,round(S,3),round(ch,3)));i=j
    g0=groups[0][0]
    print(Dq,[(round(e-g0,4),dg,m,c) for e,dg,m,c in groups[:6]])
EOF
