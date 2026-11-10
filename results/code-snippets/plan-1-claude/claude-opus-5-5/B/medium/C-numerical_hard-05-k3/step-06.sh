cat > run.py <<'EOF'
import numpy as np, itertools
from math import factorial as f, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0 or abs(m1)>j1 or abs(m2)>j2 or abs(m3)>j3: return 0.0
    t=sqrt(f(j1+j2-j3)*f(j1-j2+j3)*f(-j1+j2+j3)/f(j1+j2+j3+1))
    t*=sqrt(f(j1+m1)*f(j1-m1)*f(j2+m2)*f(j2-m2)*f(j3+m3)*f(j3-m3))
    s=0
    for k in range(0,100):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        s+=(-1)**k/np.prod([f(x) for x in a])
    return (-1)**(j1-j2-m3)*t*s
l=2
def ck(k,m1,m2):
    return (-1)**m1*(2*l+1)*w3j(l,k,l,0,0,0)*w3j(l,k,l,-m1,m1-m2,m2)
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
NE=6
dets=list(itertools.combinations(range(10),NE)); idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def apply(d,rem,add):
    new=list(d)
    for p,q in zip(rem,add): new[new.index(p)]=q
    if len(set(new))<len(new): return None,0
    arr=new[:]; sign=1
    for i in range(len(arr)):
        for j in range(len(arr)-1-i):
            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
    return idx[tuple(arr)],sign
def build(Dq,B,C):
    F4=C/35; F2=B+5*F4; F={2:F2,4:F4}
    def g(a,b,c,d):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.0
        return sum(ck(k,ma,mc)*ck(k,md,mb)*F[k] for k in (2,4))
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,2:1}[abs(m)]*Dq
    V[0,4]=V[4,0]=5*Dq
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        occ=set(d)
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[ms.index(orbs[q][0]),ms.index(orbs[p][0])]
                if v==0: continue
                if q==p: H[I,I]+=v; continue
                J,s=apply(d,[p],[q])
                if J is not None: H[J,I]+=s*v
        for p,q in itertools.combinations(d,2):
            for r,s_ in itertools.permutations(range(10),2):
                v=0.5*(g(r,s_,p,q)-g(r,s_,q,p))
                if abs(v)<1e-12: continue
                if (r in occ and r not in (p,q)) or (s_ in occ and s_ not in (p,q)): continue
                # a_r+ a_s+ a_q a_p : replace p->r? careful: use sequential mapping
                new=[x for x in d]
                # remove p,q then add s then r at front; compute sign via ordering
                lst=list(d); sign=1
                for x in (p,q):
                    k=lst.index(x); sign*=(-1)**k; lst.pop(k)
                # a_q a_p |..> : apply a_p first
                # recompute properly
                lst=list(d); sign=1
                k=lst.index(p); sign*=(-1)**k; lst.pop(k)
                k=lst.index(q); sign*=(-1)**k; lst.pop(k)
                for x in (s_,r):
                    if x in lst: sign=0;break
                    k=sum(1 for y in lst if y<x); sign*=(-1)**k; lst.insert(k,x)
                if sign==0: continue
                H[idx[tuple(lst)],I]+=sign*v
    return H
def S2():
    Sp=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p in d:
            m,s=orbs[p]
            if s==0:
                q=orbs.index((m,1))
                lst=list(d); k=lst.index(p); sign=(-1)**k; lst.pop(k)
                if q in lst: continue
                k=sum(1 for y in lst if y<q); sign*=(-1)**k; lst.insert(k,q)
                Sp[idx[tuple(lst)],I]+=sign
    Sz=np.diag([sum(0.5 if orbs[p][1] else -0.5 for p in d) for d in dets])
    return Sp.T@Sp+Sz@Sz-Sz
np.save('mats.npy',np.array([build(1,0,0),build(0,1,0),build(0,0,1),S2()]))
EOF
python3 run.py && python3 - <<'EOF'
import numpy as np
H1,HB,HC,S2=np.load('mats.npy')
# free ion check: d6 terms with B=1,C=4.5
w=np.linalg.eigvalsh(HB+4.5*HC); w-=w.min()
print(np.unique(np.round(w,4)))
print(np.allclose(H1,H1.T),np.allclose(HB,HB.T))
EOF