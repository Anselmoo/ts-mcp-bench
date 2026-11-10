mkdir -p /tmp/w && cd /tmp/w && cat > d4.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2
def so(m,s): return (m+2)*2+s
N=20
def Ck(m,q,mp,k):
    if m!=mp+q: return 0.0
    red = (-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return float((-1)**(l-m))*float(wigner_3j(l,k,l,-m,q,mp))*red
def angular(k,a,b,c,d):
    tot=0.0
    for q in range(-k,k+1):
        x=Ck(a,q,c,k)
        if x==0: continue
        y=Ck(b,-q,d,k)
        tot+=(-1)**q*x*y
    return tot
def Vel(F):
    V=np.zeros((N,N,N,N))
    ms=range(-2,3)
    for ma,mb,mc,md in itertools.product(ms,repeat=4):
        ang={k:angular(k,ma,mb,mc,md) for k in (0,2,4) if F[k]!=0}
        if not ang: continue
        base=sum(F[k]*ang[k] for k in ang)
        for sa,sb in itertools.product(range(2),repeat=2):
            V[so(ma,sa),so(mb,sb),so(mc,sa),so(md,sb)]=base
    return V
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=np.sqrt(2)
orbs={
 'xy':vec({2:1/(1j*r2),-2:-1/(1j*r2)}),
 'xz':vec({1:1/r2,-1:-1/r2}),
 'yz':vec({1:1j/r2,-1:1j/r2}),
 'z2':vec({0:1}),
 'dx2':vec({2:1/r2,-2:1/r2}),
}
t2g=['xy','xz','yz']; eg=['z2','dx2']
def h1(Dq):
    h=np.zeros((N,N),complex)
    for name,e in [(n,-4*Dq) for n in t2g]+[(n,6*Dq) for n in eg]:
        v=orbs[name]
        M=np.outer(v,v.conj())
        for s in range(2):
            for m1 in range(5):
                for m2 in range(5):
                    h[so(m1-2,s),so(m2-2,s)]+=e*M[m1,m2]
    return h
dets=list(itertools.combinations(range(N),4))
idx={d:i for i,d in enumerate(dets)}
def create_annih(occ,ann,cre):
    # apply a_cre^dag a_ann to occ list; return (newtuple,sign) or None
    occ=list(occ); s=1
    if ann==cre: return tuple(occ),1
    if cre in occ: return None
    p=occ.index(ann); s*=(-1)**p; occ.pop(p)
    if cre in occ: return None
    p=sum(1 for x in occ if x<cre); s*=(-1)**p; occ.insert(p,cre)
    return tuple(occ),s
def build(F,Dq):
    V=Vel(F); h=h1(Dq)
    n=len(dets); H=np.zeros((n,n),complex)
    for J,det in enumerate(dets):
        for c in det:
            for a in range(N):
                if abs(h[a,c])<1e-14: continue
                r=create_annih(det,c,a)
                if r: H[idx[r[0]],J]+=h[a,c]*r[1]
        for c,d in itertools.permutations(det,2):
            for a,b in itertools.permutations(range(N),2):
                v=V[a,b,c,d]
                if abs(v)<1e-14: continue
                occ=list(det); s=1
                p=occ.index(c); s*=(-1)**p; occ.pop(p)
                if d not in occ: continue
                p=occ.index(d); s*=(-1)**p; occ.pop(p)
                if b in occ: continue
                p=sum(1 for x in occ if x<b); s*=(-1)**p; occ.insert(p,b)
                if a in occ: continue
                p=sum(1 for x in occ if x<a); s*=(-1)**p; occ.insert(p,a)
                H[idx[tuple(occ)],J]+=0.5*v*s
    return H
EOF
python3 -c "
import d4,numpy as np
F={0:0,2:1.0,4:0.6}
V=d4.Vel(F)
print(np.abs(V-V.transpose(1,0,3,2)).max(), np.abs(V-V.transpose(2,3,0,1)).max())
H=d4.build(F,0.0); print(np.abs(H-H.conj().T).max())
"