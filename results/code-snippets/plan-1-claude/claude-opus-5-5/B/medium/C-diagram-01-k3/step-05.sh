cd $TMPDIR && cat > ts.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt, pi, N
B=828.;C=3390.
def ck(k,m1,m2): return float(N(sqrt(4*pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2)))
F={2:49*(B+C/7),4:441*C/35}
so=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
n=10
ckt={(k,a,b):ck(k,a,b) for k in (2,4) for a in range(-2,3) for b in range(-2,3)}
def two(a,b,c,d):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(ckt[k,ma,mc]*ckt[k,md,mb]*F[k] for k in (2,4))
G=np.zeros((n,n,n,n))
for a,b,c,d in itertools.product(range(n),repeat=4): G[a,b,c,d]=two(a,b,c,d)
V=np.zeros((5,5))
for m,v in zip(range(-2,3),[1,-4,6,-4,1]): V[m+2,m+2]=v
V[0,4]=V[4,0]=5
h1=np.array([[V[so[i][0]+2,so[j][0]+2] if so[i][1]==so[j][1] else 0 for j in range(n)] for i in range(n)])
dets=list(itertools.combinations(range(n),3)); idx={d:i for i,d in enumerate(dets)}
def ann(occ,o):
    if o not in occ: return None
    p=occ.index(o); return (-1)**p,occ[:p]+occ[p+1:]
def cre(occ,o):
    if o in occ: return None
    new=sorted(occ+[o]); return (-1)**new.index(o),new
def apply_op(det,ops):
    occ=list(det);sgn=1
    for typ,o in reversed(ops):
        r=(ann if typ=='a' else cre)(occ,o)
        if r is None: return None
        sgn*=r[0];occ=r[1]
    return sgn,tuple(occ)
D=len(dets)
H1=np.zeros((D,D));H2=np.zeros((D,D))
for j,d in enumerate(dets):
    for p in range(n):
      for q in range(n):
        if h1[p,q]:
          r=apply_op(d,[('c',p),('a',q)])
          if r: H1[idx[r[1]],j]+=r[0]*h1[p,q]
    for p,q,r_,s in itertools.product(range(n),repeat=4):
        g=G[p,q,r_,s]
        if abs(g)<1e-12: continue
        r=apply_op(d,[('c',p),('c',q),('a',s),('a',r_)])
        if r: H2[idx[r[1]],j]+=0.5*r[0]*g
Sp=np.zeros((D,D));Sz=np.zeros(D)
for j,d in enumerate(dets):
    Sz[j]=sum(so[o][1] for o in d)
    for m in range(-2,3):
        r=apply_op(d,[('c',so.index((m,0.5))),('a',so.index((m,-0.5)))])
        if r: Sp[idx[r[1]],j]+=r[0]
S2=Sp.T@Sp+np.diag(Sz**2+Sz)
C4=np.diag([np.exp(1j*np.pi/2*sum(so[o][0] for o in d)) for d in dets])
def levels(dq):
    dql=dq if dq>0 else 1e-4
    w,v=np.linalg.eigh(H2+dql*B*H1)
    w0=np.linalg.eigvalsh(H2+dq*B*H1)
    out=[];i=0
    while i<D:
        j=i
        while j<D and w[j]-w[i]<1e-3: j+=1
        sub=v[:,i:j]
        ws,vs=np.linalg.eigh(sub.T@S2@sub)
        for sval in sorted(set(np.round(ws,3))):
            vv=sub@vs[:,np.abs(ws-sval)<1e-3]
            S=(-1+np.sqrt(1+4*sval))/2; mult=int(round(2*S+1))
            m=vv.shape[1]//mult
            mask=np.abs(Sz-S)<1e-6
            P=vv@vv.conj().T
            ch=round(np.trace(P[np.ix_(mask,mask)]@C4[np.ix_(mask,mask)]).real)
            ir={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}[(m,ch)]
            out.append([np.mean(w0[i:j]),mult,ir])
        i=j
    out.sort(key=lambda x:x[0])
    return out
import pickle
grid=np.arange(0,4.01,0.05)
res={round(g,2):levels(g) for g in grid}
pickle.dump(res,open('res.pkl','wb'))
EOF
time python3 ts.py