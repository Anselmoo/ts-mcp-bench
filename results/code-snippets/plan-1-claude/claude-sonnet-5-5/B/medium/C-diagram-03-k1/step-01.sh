cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=806.;C=3570.
F2=49*B+7*C;F4=63*C/5;F={0:0,2:F2,4:F4}
l=2;ms=range(-2,3)
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k:return 0.
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,q,mp))
# V[a,b,c,d]=<ab|1/r|cd> spatial, a->c electron1
V=np.zeros((5,5,5,5))
for a,b,c,d in itertools.product(range(5),repeat=4):
    if a+b!=c+d:continue
    V[a,b,c,d]=sum(ck(k,a-2,c-2)*ck(k,d-2,b-2)*F[k] for k in (2,4))
so=[(m,s) for s in (0,1) for m in range(5)]
dets=[d for d in itertools.combinations(range(10),5) if sum(1 for i in d if i>=5)==2]
idx={d:i for i,d in enumerate(dets)};N=len(dets)
def apply(ops,d):  # ops list of (type,i) applied right to left
    d=list(d);sg=1
    for t,i in reversed(ops):
        if t=='a':
            if i in d: return None
            p=sum(1 for x in d if x<i);sg*=(-1)**p;d.append(i);d.sort()
        else:
            if i not in d:return None
            p=d.index(i);sg*=(-1)**p;d.remove(i)
    return tuple(d),sg
def run(Dq):
    H=np.zeros((N,N),complex)
    h=np.zeros((5,5));
    for m in range(-2,3):h[m+2,m+2]={0:6,1:-4,2:1}[abs(m)]*Dq
    h[4,0]=h[0,4]=5*Dq
    for j,d in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if so[p][1]!=so[q][1]:continue
                x=h[so[p][0],so[q][0]]
                if x==0:continue
                r=apply([('a',p),('d',q)],d)
                if r:H[idx[r[0]],j]+=x*r[1]
        for p,q,r_,s in itertools.product(range(10),repeat=4):
            # 1/2 sum <pq|rs> a+p a+q a_s a_r
            if so[p][1]!=so[r_][1] or so[q][1]!=so[s][1]:continue
            x=V[so[p][0],so[q][0],so[r_][0],so[s][0]]
            if x==0:continue
            r=apply([('a',p),('a',q),('d',s),('d',r_)],d)
            if r:H[idx[r[0]],j]+=0.5*x*r[1]
    # S2
    S2=np.zeros((N,N))
    for j,d in enumerate(dets):
        nu=sum(1 for i in d if i<5);nd=5-nu
        S2[j,j]+=(nu-nd)**2/4+(nu+nd)/2
        for m in range(5):
            r=apply([('a',m+5),('d',m),('a',0),('d',0)],d) if False else None
        for a in range(5):
            for b in range(5):
                r=apply([('a',a+5),('d',a),('a',b),('d',b+5)],d)
                if r:S2[idx[r[0]],j]+=r[1]  # S-S+ part: sum a+_{a dn} a_{a up} a+_{b up} a_{b dn}... 
    ph=np.array([np.exp(-1j*(so[i][0]-2)*np.pi/2) for i in range(10)])
    C4=np.diag([np.prod([ph[i] for i in d]) for d in dets])
    return H,S2,C4
import sys
res={}
for Dq in np.arange(0,4.01,.5):
    H,S2,C4=run(Dq*B+ (1e-3 if Dq==0 else 0))
    H=(H+H.conj().T)/2
    w,v=np.linalg.eigh(H);w-=w[0]
    out=[];i=0
    while i<len(w) and len(out)<8:
        j=i
        while j+1<len(w) and w[j+1]-w[i]<1e-3*B*0+0.05:j+=1
        U=v[:,i:j+1];n=j-i+1
        S2v=np.trace(U.conj().T@S2@U).real/n;c4=np.trace(U.conj().T@C4@U).real
        S=(-1+np.sqrt(1+4*S2v))/2
        out.append((w[i]/B,n,round(2*S+1),round(c4)))
        i=j+1
    print(Dq,[(round(a,3),n,s,c) for a,n,s,c in out[:8]])
E
python3 /tmp/a.py