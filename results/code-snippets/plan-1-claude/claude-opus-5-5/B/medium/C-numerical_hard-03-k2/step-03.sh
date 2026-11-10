
cd $TMPDIR && cat << 'EOF' > d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
CK={}
def ck(k,m1,m2):
    key=(k,m1,m2)
    if key not in CK:
        CK[key]=float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
    return CK[key]
orbs=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
def two(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*ck(k,ma,mc)*ck(k,md,mb) for k in (0,2,4) if abs(ma-mc)<=k)
def sgn(lst,removed):
    s=1;l=list(lst)
    for r in removed:
        p=l.index(r); s*=(-1)**p; l.pop(p)
    return s,l
def build(Dq,B,C):
    F4=C/35; F2=B+5*F4; F={0:0,2:F2*49,4:F4*441}
    h=np.zeros((10,10))
    for i,(m,s) in enumerate(orbs):
        h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
        for j,(m2,s2) in enumerate(orbs):
            if s==s2 and abs(m-m2)==4: h[i,j]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for J,e in enumerate(dets):
            ds=sorted(set(d)-set(e)); es=sorted(set(e)-set(d))
            if len(ds)>2: continue
            if len(ds)==0:
                v=sum(h[a,a] for a in d)
                for a,b in itertools.combinations(d,2):
                    v+=two(a,b,a,b,F)-two(a,b,b,a,F)
            elif len(ds)==1:
                a=ds[0];c=es[0]
                s1,r1=sgn(d,[a]);s2,r2=sgn(e,[c])
                v=(h[a,c]+sum(two(a,b,c,b,F)-two(a,b,b,c,F) for b in r1))*s1*s2
            else:
                a,b=ds;c,dd=es
                s1,_=sgn(d,[a,b]);s2,_=sgn(e,[c,dd])
                v=s1*s2*(two(a,b,c,dd,F)-two(a,b,dd,c,F))
            H[I,J]=v
    return H
# S^2 = S-S+ + Sz^2 + Sz, via second quantization
def apply(op_list,d):  # op: ('a',orb) annihilate or ('c',orb) create, rightmost first
    l=list(d);s=1
    for t,o in reversed(op_list):
        if t=='a':
            if o not in l: return None,0
            p=l.index(o);s*=(-1)**p;l.pop(p)
        else:
            if o in l: return None,0
            l.insert(0,o)
            # sort with sign
    # sort
    arr=l[:];sign=s
    for i in range(len(arr)):
        for j in range(len(arr)-1-i):
            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j];sign=-sign
    return tuple(arr),sign
N=len(dets);S2=np.zeros((N,N))
up=lambda m:orbs.index((m,1));dn=lambda m:orbs.index((m,0))
for I,d in enumerate(dets):
    sz=sum(0.5 if orbs[o][1]==1 else -0.5 for o in d)
    S2[I,I]+=sz*sz+sz
    for m1 in ms:
        for m2 in ms:
            # S- S+ = sum c†_{m1 dn} a_{m1 up} c†_{m2 up} a_{m2 dn}
            t,s=apply([('c',dn(m1)),('a',up(m1)),('c',up(m2)),('a',dn(m2))],d)
            if t: S2[idx[t],I]+=s
def levels(Dq,B,C):
    H=build(Dq,B,C)
    w,v=np.linalg.eigh(H)
    s=np.einsum('ji,jk,ki->i',v,S2,v)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-4: j+=1
        out.append((round(w[i],1),j-i,round(s[i],2))); i=j
    return out
EOF
cat << 'EOF' > run.py
exec(open('d5.py').read())
for l in levels(3000,600,2760)[:12]: print(l)
EOF
time python3 run.py
