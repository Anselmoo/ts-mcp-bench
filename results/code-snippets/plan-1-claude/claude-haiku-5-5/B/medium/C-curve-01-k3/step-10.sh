cat << 'EOF' > /dev/null
EOF
cat << 'EOF' | python3 -
import numpy as np, itertools
from scipy.linalg import expm
from sympy.physics.wigner import wigner_3j
l=2; ms=list(range(-2,3))
def red(k): return (-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
def C(k,q,m,mp):
    if m!=mp+q: return 0.0
    return (-1)**(l-m)*float(wigner_3j(l,k,l,-m,q,mp))*red(k)
def ang(k,a,c,b,d):
    return sum((-1)**q*C(k,q,a,c)*C(k,-q,b,d) for q in range(-k,k+1))
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
nel=4
states=list(itertools.combinations(range(10),nel)); idx={s:i for i,s in enumerate(states)}
N=len(states)
def apply_pair(st,p,q,r,s_):
    occ=list(st); sign=1
    if r not in occ: return None,0
    pos=occ.index(r); sign*=(-1)**pos; occ.pop(pos)
    if s_ not in occ: return None,0
    pos=occ.index(s_); sign*=(-1)**pos; occ.pop(pos)
    if q in occ: return None,0
    pos=sum(1 for x in occ if x<q); sign*=(-1)**pos; occ.insert(pos,q)
    if p in occ: return None,0
    pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
    return tuple(occ),sign
M={}
for k in (2,4):
    A=np.zeros((N,N))
    for p in range(10):
      for q in range(10):
        for r in range(10):
          for s_ in range(10):
            mp,sp=orbs[p]; mq,sq=orbs[q]; mr,sr=orbs[r]; mss,ss=orbs[s_]
            if sp!=sr or sq!=ss: continue
            val=ang(k,mp,mr,mq,mss)
            if abs(val)<1e-14: continue
            for ci,st in enumerate(states):
                new,sg=apply_pair(st,p,q,r,s_)
                if new is None: continue
                A[idx[new],ci]+=0.5*val*sg
    M[k]=A
diag={-2:1,-1:-4,0:6,1:-4,2:1}
one=np.zeros((10,10))
for i,(m,s) in enumerate(orbs): one[i,i]=diag[m]
for i,(m,s) in enumerate(orbs):
    for j,(m2,s2) in enumerate(orbs):
        if s==s2 and ((m==2 and m2==-2) or (m==-2 and m2==2)): one[i,j]=5
H1=np.zeros((N,N))
for ci,st in enumerate(states):
    for p in range(10):
        for r in range(10):
            if one[p,r]==0: continue
            occ=list(st)
            if r not in occ: continue
            pos=occ.index(r); sg=(-1)**pos; occ.pop(pos)
            if p in occ: continue
            pos=sum(1 for x in occ if x<p); sg*=(-1)**pos; occ.insert(pos,p)
            H1[idx[tuple(occ)],ci]+=one[p,r]*sg
Sp=np.zeros((N,N))
for ci,st in enumerate(states):
    for a in range(10):
        for b in range(10):
            if orbs[a][0]!=orbs[b][0] or orbs[a][1]!=0.5 or orbs[b][1]!=-0.5: continue
            occ=list(st)
            if b not in occ or a in occ: continue
            pos=occ.index(b); sg=(-1)**pos; occ.pop(pos)
            pos=sum(1 for x in occ if x<a); sg*=(-1)**pos; occ.insert(pos,a)
            Sp[idx[tuple(occ)],ci]+=sg
Sm=Sp.T
Sz=np.diag([sum(0.5 if orbs[x][1]>0 else -0.5 for x in st) for st in states])
S2=Sm@Sp+Sz@Sz+Sz
# single-particle generators in spin-orbital basis
Lz=np.diag([m+0j for m,s in orbs])
Lp=np.zeros((10,10),complex); 
for i,(m,s) in enumerate(orbs):
    for j,(m2,s2) in enumerate(orbs):
        if s==s2 and m2==m+1: Lp[j,i]=np.sqrt(l*(l+1)-m*(m+1))
Lm=Lp.conj().T
Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j)
Szs=np.diag([0.5 if s>0 else -0.5 for m,s in orbs]).astype(complex)
Spp=np.zeros((10,10),complex)
for i,(m,s) in enumerate(orbs):
    for j,(m2,s2) in enumerate(orbs):
        if m==m2 and s==-0.5 and s2==0.5: Spp[j,i]=1
Smm=Spp.conj().T
Sxs=(Spp+Smm)/2; Sys=(Spp-Smm)/(2j)
J=[Lx+Sxs,Ly+Sys,Lz+Szs]
def Ugen(n,th):
    Jn=n[0]*J[0]+n[1]*J[1]+n[2]*J[2]
    return expm(-1j*th*Jn)
def manybody(U):
    W=np.zeros((N,N),complex)
    for ci,st in enumerate(states):
        cols=list(st)
        for ri,rs in enumerate(states):
            W[ri,ci]=np.linalg.det(U[np.ix_(list(rs),cols)])
    return W
def unit(v): v=np.array(v,float); return v/np.linalg.norm(v)
ops=[]  # (class size, U)
ops.append((1,np.eye(10,dtype=complex)))
ops.append((8,Ugen(unit([1,1,1]),2*np.pi/3)))
ops.append((3,Ugen([0,0,1],np.pi)))
ops.append((6,Ugen([0,0,1],np.pi/2)))
ops.append((6,Ugen(unit([1,1,0]),np.pi)))
# O character table order: E, 8C3, 3C2, 6C4, 6C2'
irr={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
Ws=[manybody(U) for _,U in ops]
sizes=[c for c,_ in ops]
def decompose(vecs):
    out={}
    for name,ch in irr.items():
        # character of group rep on subspace: trace(V^dag W V)
        tot=0
        for (c,W),chi_ in zip(zip(sizes,Ws),range(5)):
            pass
        s=0
        for idxc,(c,W) in enumerate(zip(sizes,Ws)):
            chi=np.trace(vecs.conj().T@W@vecs)
            s+=c*chi*ch[idxc]
        out[name]=round((s/24).real,3)
    return out
for Dq in [0.9,2.15,3.35]:
    H=F2*M[2]+F4*M[4]+Dq*H1 if False else None
EOF
echo