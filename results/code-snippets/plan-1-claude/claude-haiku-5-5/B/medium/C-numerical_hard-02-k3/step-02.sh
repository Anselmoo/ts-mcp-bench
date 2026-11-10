mkdir -p /w && cat > /w/d4.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
l=2
# spin orbitals: (m,s) index = (m+2)*2+s  s:0 up,1 down
def so(m,s): return (m+2)*2+s
N=20
def cg(k,q,mp,m):  # <l m|C^k_q|l m'> with m=mp? implement generic
    pass
def Ck(m,q,mp,k):
    # <l m|C^k_q|l mp>
    if m!=mp+q: return 0.0
    red = (-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return float((-1)**(l-m))*float(wigner_3j(l,k,l,-m,q,mp))*red
def angular(k,a,b,c,d):
    # <m_a m_b|C^k.C^k|m_c m_d>, a,b,c,d are m values; q=mc-ma... handled by Ck
    tot=0.0
    for q in range(-k,k+1):
        x=Ck(a,q,c,k)
        if x==0: continue
        y=Ck(b,-q,d,k)
        tot+=(-1)**q*x*y
    return tot
def Vel(F):
    # V[i,j,k,l] = <ij|V|kl> in spin orbitals, <ij|V|kl>=sum_k F^k angular, spin conservation
    V=np.zeros((N,N,N,N))
    ms=range(-2,3)
    for ma,mb,mc,md in itertools.product(ms,repeat=4):
        for sa,sb,sc,sd in itertools.product(range(2),repeat=4):
            if sa!=sc or sb!=sd: continue
            val=0.0
            for k in (0,2,4):
                if F[k]==0: continue
                val+=F[k]*angular(k,ma,mb,mc,md)
            V[so(ma,sa),so(mb,sb),so(mc,sc),so(md,sd)]=val
    return V
# real-orbital coefficients in m basis
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
# one-electron matrix in m basis (spin-diag), field: t2g -4Dq, eg +6Dq
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
# determinants: 4 electrons among 20 spin-orbitals
dets=list(itertools.combinations(range(N),4))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det, ops):
    # ops list of (type,i): applied right to left in order given (rightmost first)
    occ=list(det); sign=1
    for typ,i in ops:
        if typ=='a':  # annihilate
            if i not in occ: return None,0
            p=occ.index(i); sign*= (-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            # insert at sorted position
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
def build(F,Dq):
    V=Vel(F); h=h1(Dq)
    n=len(dets); H=np.zeros((n,n),complex)
    for J,det in enumerate(dets):
        # one-body
        for c in det:
            for a in range(N):
                if abs(h[a,c])<1e-14: continue
                # a_a^dag a_c |J>
                new,sg=apply_ops(det,[('a',c),('c',a)]) if False else (None,0)
                occ=list(det)
                if a==c: new,sg=det,1
                else:
                    if a in occ: continue
                    p=occ.index(c); s1=(-1)**p; occ.pop(p)
                    p2=sum(1 for x in occ if x<a); s2=(-1)**p2; occ.insert(p2,a)
                    new=tuple(occ); sg=s1*s2
                H[idx[new],J]+=h[a,c]*sg
        # two-body: 1/2 sum V[a,b,c,d] a_a^dag a_b^dag a_d a_c
        for c,d in itertools.permutations(det,2):
            for a,b in itertools.permutations(range(N),2):
                v=V[a,b,c,d]
                if abs(v)<1e-14: continue
                # a_d a_c first (c then d: a_d a_c |J> = a_d (a_c|J>)), then a_b^dag a_a^dag
                occ=list(det); sign=1
                # annihilate c
                p=occ.index(c); sign*=(-1)**p; occ.pop(p)
                if d not in occ: continue
                p=occ.index(d); sign*=(-1)**p; occ.pop(p)
                # create b then a: a_a^dag a_b^dag |occ>  -> first create b
                if b in occ: continue
                p=sum(1 for x in occ if x<b); sign*=(-1)**p; occ.insert(p,b)
                if a in occ: continue
                p=sum(1 for x in occ if x<a); sign*=(-1)**p; occ.insert(p,a)
                H[idx[tuple(occ)],J]+=0.5*v*sign
    return H
EOF
cd /w && python3 -c "
import d4,numpy as np
F={0:0,2:1.0,4:0.6}
V=d4.Vel(F)
print(np.abs(V-V.transpose(1,0,3,2)).max(), np.abs(V-V.transpose(2,3,0,1)).max())
"