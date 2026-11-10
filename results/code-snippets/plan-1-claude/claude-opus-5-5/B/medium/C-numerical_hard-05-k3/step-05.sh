python3 - <<'EOF'
import numpy as np, itertools
from math import factorial as f, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    t=sqrt(f(j1+j2-j3)*f(j1-j2+j3)*f(-j1+j2+j3)/f(j1+j2+j3+1))
    t*=sqrt(f(j1+m1)*f(j1-m1)*f(j2+m2)*f(j2-m2)*f(j3+m3)*f(j3-m3))
    s=0
    for k in range(0,100):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        s+=(-1)**k/np.prod([f(x) for x in a])
    return (-1)**(j1-j2-m3)*t*s
l=2
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return (-1)**m1*(2*l+1)*w3j(l,k,l,0,0,0)*w3j(l,k,l,-m1,m1-m2,m2)
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def build(Dq,B,C):
    F4=C/35; F2=B+5*F4; F={0:0,2:F2,4:F4}
    # two-electron integral <ab|g|cd> spin orbitals
    def g(a,b,c,d):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.0
        return sum(ck(k,ma,mc)*ck(k,md,mb)*F[k] for k in (2,4))
    V=np.zeros((5,5))
    for i,m in enumerate(ms):
        V[i,i]={0:6,1:-4,2:1}[abs(m)]*Dq
    V[0,4]=V[4,0]=5*Dq
    dets=list(itertools.combinations(range(10),6))
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets); H=np.zeros((N,N)); S2=np.zeros((N,N))
    for I,d in enumerate(dets):
        occ=set(d)
        # one-body
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[ms.index(orbs[q][0]),ms.index(orbs[p][0])]
                if v==0: continue
                if q!=p and q in occ: continue
                new=list(d); pos=new.index(p); new[pos]=q
                sign=1
                # sort with sign
                arr=new[:]
                for i in range(len(arr)):
                    for j in range(len(arr)-1-i):
                        if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
                H[idx[tuple(arr)],I]+=sign*v
        # two-body: sum_{p<q} sum_{r<s} (<rs|pq>-<rs|qp>) a_r+ a_s+ a_q a_p
        for p,q in itertools.combinations(d,2):
            rest=[x for x in d if x not in (p,q)]
            for r,s in itertools.combinations(range(10),2):
                if r in rest or s in rest: continue
                v=g(r,s,p,q)-g(r,s,q,p)
                if abs(v)<1e-12: continue
                # build new det: replace p->r, q->s in place
                new=list(d); new[new.index(p)]=r; new[new.index(q)]=s
                arr=new[:]; sign=1
                for i in range(len(arr)):
                    for j in range(len(arr)-1-i):
                        if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
                H[idx[tuple(arr)],I]+=sign*v
        # S^2 diag partially: use Sz^2 + Sz + S-S+
    # S^2 via operators
    def Sminus_Splus():
        M=np.zeros((N,N))
        Sp=np.zeros((N,N))
        for I,d in enumerate(dets):
            for p in d:
                m,s=orbs[p]
                if s==0:
                    q=orbs.index((m,1))
                    if q in d: continue
                    new=list(d); new[new.index(p)]=q; arr=new[:]; sign=1
                    for i in range(len(arr)):
                        for j in range(len(arr)-1-i):
                            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
                    Sp[idx[tuple(arr)],I]+=sign
        Sz=np.diag([sum(0.5 if orbs[p][1]==1 else -0.5 for p in d) for d in dets])
        return Sp.T@Sp+Sz@Sz+Sz
    return H,Sminus_Splus()
import pickle
H1,S2=build(1,0,0); HB,_=build(0,1,0); HC,_=build(0,0,1)
np.save('mats.npy',np.array([H1,HB,HC,S2]))
EOF
ls