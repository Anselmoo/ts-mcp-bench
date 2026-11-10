cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):  # c^k(l m1, l m2)
    from sympy.physics.wigner import wigner_3j
    l=2
    return float((-1)**m1*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m1,m1-m2,m2))
C={k:{(a,b):ck(k,a,b) for a in ms for b in ms} for k in (2,4)}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
def two(a,b,c,d,F):  # <ab|g|cd>
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=[so[x] for x in (a,b,c,d)]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.
    return sum(F[k]*C[k][(m1,m3)]*C[k][(m4,m2)] for k in (2,4))
def build(Dq,B,Cc):
    F2=B+Cc/7; F4=Cc/35; F={2:49*F2,4:441*F4}
    V=np.zeros((5,5))
    d={-2:Dq,2:Dq,0:6*Dq,1:-4*Dq,-1:-4*Dq}
    for i,m in enumerate(ms): V[i,i]=d[m]
    V[0,4]=V[4,0]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    for I,D in enumerate(dets):
        Ds=set(D)
        # one-body
        for p in D:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                val=V[ms.index(so[q][0]),ms.index(so[p][0])]
                if val==0: continue
                if q!=p and q in Ds: continue
                new=list(D); pos=new.index(p); new[pos]=q
                sign=1
                # sort with sign
                arr=new[:]
                for i in range(len(arr)):
                    for j in range(len(arr)-1-i):
                        if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
                H[idx[tuple(arr)],I]+=sign*val
        # two-body: sum_{p<q in D} sum_{r<s} (<rs|pq>-<rs|qp>) a_r+ a_s+ a_q a_p
        for p,q in itertools.combinations(D,2):
            rest=[x for x in D if x not in (p,q)]
            for r,s in itertools.combinations(range(10),2):
                if r in rest or s in rest: continue
                val=two(r,s,p,q,F)-two(r,s,q,p,F)
                if abs(val)<1e-12: continue
                # apply a_q a_p then a_s+ a_r+ ... use ordered list ops
                def ann(lst,x):
                    i=lst.index(x); return (-1)**i, lst[:i]+lst[i+1:]
                def cre(lst,x):
                    i=sum(1 for y in lst if y<x); return (-1)**i, sorted(lst+[x])
                sg=1;l=list(D)
                a,l=ann(l,p);sg*=a
                a,l=ann(l,q);sg*=a
                a,l=cre(l,s);sg*=a
                a,l=cre(l,r);sg*=a
                H[idx[tuple(l)],I]+=sg*val
    return H
# S^2
def Sz(D): return sum(0.5 if so[x][1] else -0.5 for x in D)
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc)
    sel=[i for i,D in enumerate(dets) if Sz(D)==1.5]
    sel2=[i for i,D in enumerate(dets) if Sz(D)==2.5]
    e5=np.linalg.eigvalsh(H[np.ix_(sel2,sel2)])
    e3=np.linalg.eigvalsh(H[np.ix_(sel,sel)])
    # quartet levels: those in Sz=3/2 not in Sz=5/2
    e3=list(np.round(e3,6)); 
    for e in np.round(e5,6):
        for j,x in enumerate(e3):
            if abs(x-e)<1e-4: e3.pop(j);break
    g=min(e5); e3=sorted(np.array(e3)-g)
    # group
    out=[];
    for x in e3:
        if out and abs(out[-1][0]-x)<1e-3: out[-1][1]+=1
        else: out.append([x,1])
    return out
print(levels(800,700,3000)[:6])
EOF
python3 -c "
exec(open('/tmp/d5.py').read())
"