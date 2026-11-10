cd /tmp && cat > /tmp/fit_src.txt << 'EOF'
EOF
python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
def sph_harm(m,l,ph,th): return sph_harm_y(l,m,th,ph)
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.linspace(0,2*np.pi,nph,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
Y={m:sph_harm(m,2,PH,TH) for m in range(-2,3)}
s2=1/np.sqrt(2)
orbs=[1j*(Y[-2]-Y[2])*s2, 1j*(Y[-1]+Y[1])*s2, (Y[-1]-Y[1])*s2, (Y[-2]+Y[2])*s2, Y[0]]
for i in range(5):
    orbs[i]=orbs[i]/np.sqrt(np.sum(W*np.abs(orbs[i])**2))
def ak(k):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Yk=sph_harm(q,k,PH,TH)
        M=np.array([[np.sum(W*np.conj(orbs[a])*np.conj(Yk)*orbs[c]) for c in range(5)] for a in range(5)])
        N=np.array([[np.sum(W*np.conj(orbs[b])*Yk*orbs[d]) for d in range(5)] for b in range(5)])
        A+=np.einsum('ac,bd->abcd',M,N)
    return (4*np.pi/(2*k+1)*A).real
a2,a4=ak(2),ak(4)
NS=10
states=list(itertools.combinations(range(NS),3))
idx={s:i for i,s in enumerate(states)}
D=len(states)
def cann(x,occ):
    if x not in occ: return None
    pos=occ.index(x); return (-1)**pos, occ[:pos]+occ[pos+1:]
def ccre(x,occ):
    if x in occ: return None
    pos=sum(1 for y in occ if y<x); return (-1)**pos, sorted(occ+[x])
def apply2(p,q,r,s,st):
    occ=list(st)
    o=cann(r,occ)
    if o is None: return None
    sg1,occ=o; o=cann(s,occ)
    if o is None: return None
    sg2,occ=o; o=ccre(q,occ)
    if o is None: return None
    sg3,occ=o; o=ccre(p,occ)
    if o is None: return None
    sg4,occ=o
    return sg1*sg2*sg3*sg4, tuple(occ)
def apply1(p,q,st):
    occ=list(st); o=cann(q,occ)
    if o is None: return None
    sg1,occ=o; o=ccre(p,occ)
    if o is None: return None
    sg2,occ=o
    return sg1*sg2, tuple(occ)
def twobody(G):
    H=np.zeros((D,D))
    for p in range(NS):
     for q in range(NS):
      for r in range(NS):
       for s in range(NS):
        if (p%2)!=(r%2) or (q%2)!=(s%2): continue
        val=0.5*G[p//2,q//2,r//2,s//2]
        if abs(val)<1e-14: continue
        for j,st in enumerate(states):
            o=apply2(p,q,r,s,st)
            if o is None: continue
            H[idx[o[1]],j]+=o[0]*val
    return H
eps=[-4.0]*3+[6.0]*2
F=np.diag([sum(eps[p//2] for p in st) for st in states])
T2=twobody(a2); T4=twobody(a4)
Sz=np.diag([sum(0.5 if p%2==0 else -0.5 for p in st) for st in states])
Sp=np.zeros((D,D)); Sm=np.zeros((D,D))
for o_ in range(5):
    for j,st in enumerate(states):
        r=apply1(2*o_,2*o_+1,st)
        if r is not None: Sp[idx[r[1]],j]+=r[0]
        r=apply1(2*o_+1,2*o_,st)
        if r is not None: Sm[idx[r[1]],j]+=r[0]
Sop=Sm@Sp+Sz@Sz+Sz
w_,v=np.linalg.eigh(Sop)
VQ=v[:,np.abs(w_-3.75)<1e-6]; VD=v[:,np.abs(w_-0.75)<1e-6]
def levels(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    H=Dq*F+F2*T2+F4*T4
    H=0.5*(H+H.T)
    q=np.linalg.eigvalsh(VQ.T@H@VQ); d=np.linalg.eigvalsh(VD.T@H@VD)
    return q,d
def group(vals,tol=1e-3):
    out=[]; 
    for v_ in np.sort(vals):
        if out and abs(v_-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([v_,1])
    return out
# Test: B=0.8? choose B=860,C=3500 (Cr3+ like), Dq=1750
B,C=860.,3500.
for Dq in [0.0,1750.0]:
    q,d=levels(Dq,B,C)
    g0=q.min()
    print("Dq",Dq)
    print(" quartets:",[(round(a-g0,1),m) for a,m in group(q)])
    print(" doublets:",[(round(a-g0,1),m) for a,m in group(d)])
EOF