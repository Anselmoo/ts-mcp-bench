cd /tmp && python3 - << 'EOF'
import numpy as np, itertools
from scipy.optimize import brentq
xg, wg = np.polynomial.legendre.leggauss(14)
nphi=28
pts=[]; ws=[]
for ct, w in zip(xg, wg):
    st=np.sqrt(1-ct*ct)
    for ph in np.linspace(0,2*np.pi,nphi,endpoint=False):
        pts.append([st*np.cos(ph), st*np.sin(ph), ct]); ws.append(w*2*np.pi/nphi)
P=np.array(pts); W=np.array(ws)
x,y,z=P.T
funcs=[x*y, y*z, x*z, 2*z*z-x*x-y*y, x*x-y*y]
F=np.array([f/np.sqrt(np.sum(W*f*f)) for f in funcs])
g=np.clip(P@P.T,-1,1)
A=F*W
Ik={}
for k in [0,2,4]:
    M=np.polynomial.legendre.Legendre.basis(k)(g)
    Ik[k]=np.einsum('ap,cp,pq,bq,dq->acbd', A, F, M, A, F, optimize=True)
def slater(B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    return {0:0.0,2:F2,4:F4}
Fk=slater(803.0,3078.0)
def V(i,j,k,l):
    mi,si=divmod(i,2); mj,sj=divmod(j,2); mk,sk=divmod(k,2); ml,sl=divmod(l,2)
    if si!=sk or sj!=sl: return 0.0
    return sum(Fk[kk]*Ik[kk][mi,mk,mj,ml] for kk in [0,2,4])
states=[sum(1<<o for o in occ) for occ in itertools.combinations(range(10),6)]
idx={s:n for n,s in enumerate(states)}
D=len(states)
def op(s, ops):
    sign=1
    for typ,o in reversed(ops):
        n=bin(s & ((1<<o)-1)).count('1')
        if typ=='a':
            if not (s>>o)&1: return None,0
            s&=~(1<<o)
        else:
            if (s>>o)&1: return None,0
            s|=(1<<o)
        if n%2: sign=-sign
    return s,sign
quads=[(i,j,k,l,V(i,j,k,l)) for i,j,k,l in itertools.product(range(10),repeat=4) if i!=j and k!=l and abs(V(i,j,k,l))>1e-12]
def hamiltonian(Dq):
    h=np.zeros(10)
    for m in range(5):
        e=-4*Dq if m<3 else 6*Dq
        h[2*m]=h[2*m+1]=e
    H=np.zeros((D,D))
    for s in states:
        c=idx[s]
        H[c,c]+=sum(h[o] for o in range(10) if (s>>o)&1)
        for i,j,k,l,v in quads:
            s1,s1s=op(s,[('a',k)])
            if s1 is None: continue
            s2,s2s=op(s1,[('a',l)])
            if s2 is None: continue
            s3,s3s=op(s2,[('c',j)])
            if s3 is None: continue
            s4,s4s=op(s3,[('c',i)])
            if s4 is None: continue
            H[idx[s4],c]+=0.5*v*s1s*s2s*s3s*s4s
    return H
Sp=np.zeros((D,D)); Sz=np.zeros((D,D))
for s in states:
    c=idx[s]
    for m in range(5):
        t,sg=op(s,[('c',2*m),('a',2*m+1)])
        if t is not None: Sp[idx[t],c]+=sg
    Sz[c,c]=0.5*sum((s>>(2*m)&1)-(s>>(2*m+1)&1) for m in range(5))
S2m=Sp.T@Sp+Sz@Sz+Sz
def lowest(Dq,S):
    H=hamiltonian(Dq); w,v=np.linalg.eigh(H)
    s2=np.einsum('ia,ij,ja->a',v,S2m,v)
    return min(e for e,s in zip(w,s2) if abs(s-S*(S+1))<0.1)
f=lambda d: lowest(d,2)-lowest(d,0)
for d in np.arange(1000,1600,100): print(d, round(f(d),1))
r=brentq(f,1000,1600,xtol=1e-6)
print("Dq crossover (quintet vs singlet ground) =", r, " Dq/B=", r/803)
print("Quintet-singlet at r:", lowest(r,2), lowest(r,0))
EOF