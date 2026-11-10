mkdir -p /tmp/w && cd /tmp/w && cat > ts.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt, pi, N
B=828.;C=3390.
l=2
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return float(N(sqrt(4*pi/(2*k+1))*(-1)**m1*gaunt(l,k,l,-m1,m1-m2,m2)))
F={2:49*(B+C/7),4:441*C/35}
so=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
def two(a,b,c,d):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(ck(k,ma,mc)*ck(k,md,mb)*F[k] for k in (2,4))
n=10
G=np.zeros((n,n,n,n))
for a,b,c,d in itertools.product(range(n),repeat=4): G[a,b,c,d]=two(a,b,c,d)
V=np.zeros((5,5)); 
for m,v in zip(range(-2,3),[1,-4,6,-4,1]): V[m+2,m+2]=v
V[0,4]=V[4,0]=5
h1=np.zeros((n,n))
for i in range(n):
  for j in range(n):
    if so[i][1]==so[j][1]: h1[i,j]=V[so[i][0]+2,so[j][0]+2]
dets=list(itertools.combinations(range(n),3)); idx={d:i for i,d in enumerate(dets)}
def apply_op(det,ops):
    # ops: list of (create/annihilate, orb) applied right-to-left; returns (sign,det) or None
    occ=list(det);sgn=1
    for typ,o in reversed(ops):
        if typ=='a':
            if o not in occ: return None
            p=occ.index(o); sgn*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None
            occ.insert(0,o); # then sort
            p=sorted(occ).index(o); occ=sorted(occ); sgn*=(-1)**p
    return sgn,tuple(sorted(occ))
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
# S^2
Sp=np.zeros((D,D));Sz=np.zeros(D)
for j,d in enumerate(dets):
    Sz[j]=sum(so[o][1] for o in d)
    for m in range(-2,3):
        up=so.index((m,0.5));dn=so.index((m,-0.5))
        r=apply_op(d,[('c',up),('a',dn)])
        if r: Sp[idx[r[1]],j]+=r[0]
S2=Sp.T@Sp+np.diag(Sz**2+Sz)  # S-S+ + Sz^2+Sz ; Sp^T = S-
S2=Sp@Sp.T+np.diag(Sz**2-Sz)
C4=np.diag([np.exp(1j*np.pi/2*sum(so[o][0] for o in d)) for d in dets])
def levels(dq):
    H=H2+dq*B*H1
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<D:
        j=i
        while j<D and w[j]-w[i]<1e-4*B: j+=1
        sub=v[:,i:j]
        s2=np.linalg.eigvalsh(sub.T@S2@sub)
        # split by spin
        ws,vs=np.linalg.eigh(sub.T@S2@sub)
        for sval in sorted(set(np.round(ws,3))):
            vv=sub@vs[:,np.abs(ws-sval)<1e-3]
            S=(-1+np.sqrt(1+4*sval))/2; mult=int(round(2*S+1))
            # within Ms=S
            m=vv.shape[1]//mult
            # character: trace of C4 over spin-space with Ms restricted: use projector onto Ms=S
            P=vv@vv.conj().T
            mask=np.abs(Sz-S)<1e-6
            Pm=P[np.ix_(mask,mask)]
            ch=np.trace(Pm@C4[np.ix_(mask,mask)]).real*np.exp(-1j*np.pi/2*0).real
            # C4 also acts on spin: total Jz = Lz+Sz; we used only orbital ML so fine
            out.append((w[i],mult,m,round(ch)))
        i=j
    return out
EOF
echo