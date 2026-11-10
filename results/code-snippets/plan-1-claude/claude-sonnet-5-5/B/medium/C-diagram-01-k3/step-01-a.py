import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=828.;C=3390.
F4=63*C/5;F2=(441*B+5*F4)/9
F={2:F2,4:F4}
ms=range(-2,3)
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k:return 0.
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,q,mp))
cc={(k,m,mp):ck(k,m,mp) for k in(2,4) for m in ms for mp in ms}
so=[(m,s) for m in ms for s in(0,1)]
def g(a,b,c,d): # <ab|cd>
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]:return 0.
    return sum(cc[(k,a[0],c[0])]*cc[(k,d[0],b[0])]*F[k] for k in(2,4))
dets=[c for c in itertools.combinations(range(10),3)]
idx={d:i for i,d in enumerate(dets)}
def apply(op,det):  # op list of (creators..) simple: a†_p a†_q a_s a_r
    pass
def two(p,q,r,s,det):
    # a†p a†q a_s a_r |det>
    l=list(det);sign=1
    for o in (r,s):
        if o not in l:return None
        i=l.index(o);sign*=(-1)**i;l.pop(i)
    for o in (q,p):
        if o in l:return None
        # insert at front
        l.insert(0,o);
        # sort
        pass
    # recompute sign by sorting
    arr=l;perm=0
    # count inversions
    for i in range(len(arr)):
        for j in range(i+1,len(arr)):
            if arr[i]>arr[j]:perm+=1
    return tuple(sorted(arr)),sign*(-1)**perm
def build(Dq):
    H=np.zeros((120,120),complex)
    V={2:1,-2:1,1:-4,-1:-4,0:6}
    for d in dets:
        i=idx[d]
        for o in d: H[i,i]+=Dq*V[so[o][0]]
        for o in d:
            if so[o][0]==2:
                t=list(d);t.remove(o)
                n=so.index((-2,so[o][1]))
                if n not in t:
                    t2=t+[n];perm=sum(1 for a in range(3) for b in range(a+1,3) if t2[a]>t2[b])
                    # position-sign
                    pos=d.index(o)
                    # removal at pos then append at end: sign (-1)^(pos)*(-1)^(2-0)?? handle by explicit
                    arr=list(d);arr[pos]=n
                    inv=sum(1 for a in range(3) for b in range(a+1,3) if arr[a]>arr[b])
                    H[idx[tuple(sorted(arr))],i]+=5*Dq*(-1)**inv
            if so[o][0]==-2:
                n=so.index((2,so[o][1]));pos=d.index(o);arr=list(d)
                if n not in arr:
                    arr[pos]=n
                    inv=sum(1 for a in range(3) for b in range(a+1,3) if arr[a]>arr[b])
                    H[idx[tuple(sorted(arr))],i]+=5*Dq*(-1)**inv
    for p in range(10):
     for q in range(10):
      for r in range(10):
       for s in range(10):
        if p==q or r==s:continue
        v=0.5*g(so[p],so[q],so[r],so[s]) if False else None
    # H2 = 1/2 sum <pq|rs> a†p a†q a_s a_r
    G={}
    for p in range(10):
     for q in range(10):
      for r in range(10):
       for s in range(10):
        if p!=q and r!=s:
         x=g(so[p],so[q],so[r],so[s])
         if x:G[(p,q,r,s)]=x
    for d in dets:
        i=idx[d]
        for (p,q,r,s),x in G.items():
            res=two(p,q,r,s,d)
            if res:H[idx[res[0]],i]+=0.5*x*res[1]
    return H
U=np.diag([np.exp(-1j*m*np.pi/2) for m,s in so])
def Cop():
    M=np.zeros((120,120),complex)
    for d in dets:
        for e in dets:
            M[idx[e],idx[d]]=np.linalg.det(U[np.ix_(e,d)])
    return M
Cm=Cop()
Sz=lambda d:sum(1 if so[o][1]==0 else -1 for o in d)/2
S2=np.zeros((120,120))
# S^2 via sz and S-S+: use H + lambda S2 trick unnecessary; label spin from degeneracy via Sz sector
sz=np.array([Sz(d) for d in dets])
def spinlab(S):return {1.5:'4',0.5:'2'}[S]
res={}
import sys
for Dq in np.arange(0,4.01,.5)*B:
    H=build(Dq);assert np.allclose(H,H.conj().T,atol=1e-6)
    out=[]
    # Sz=3/2 sector -> quartets ; Sz=1/2 -> quartets+doublets ; use Sz=1/2 and remove quartet energies
    for s_ in (1.5,0.5):
        ix=np.where(sz==s_)[0]
        h=H[np.ix_(ix,ix)];c=Cm[np.ix_(ix,ix)]
        w,v=np.linalg.eigh(h)
        i=0
        while i<len(w):
            j=i
            while j+1<len(w) and abs(w[j+1]-w[i])<1e-6:j+=1
            sub=v[:,i:j+1];n=j-i+1
            ch=np.trace(sub.conj().T@c@sub).real
            out.append((w[i],s_,n,round(ch)));i=j+1
        if s_==1.5:q=[(o[0],o[2],o[3]) for o in out]
    # remove quartets from sz=.5 list
    fin=[]
    for o in out[len(q):]:
        if any(abs(o[0]-x[0])<1e-6 and o[2]==x[1] for x in q):continue
        fin.append(o)
    allv=[(o[0],'4',o[2],o[3]) for o in out[:len(q)]]+[(o[0],'2',o[2],o[3]) for o in fin]
    allv.sort()
    print(Dq/B,[(round((a-allv[0][0])/B,3),b,n,c) for a,b,n,c in allv[:9]])
