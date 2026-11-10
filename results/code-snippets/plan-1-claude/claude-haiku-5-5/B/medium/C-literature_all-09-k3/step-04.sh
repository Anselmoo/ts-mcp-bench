mkdir -p /tmp/w && cd /tmp/w && cat > ligf.py << 'EOF'
import numpy as np
from sympy.physics.wigner import gaunt
from functools import lru_cache

orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
n=len(orbs)
@lru_cache(None)
def G(k,q,m,mp):
    if abs(q)>k or abs(m)>2 or abs(mp)>2: return 0.0
    val=gaunt(2,k,2,-m,q,mp)
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m*val)
def Vsp(m1,m2,m3,m4,F):
    tot=0.0
    for k,Fk in zip((0,2,4),F):
        if Fk==0: continue
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*G(k,-q,m1,m3)*G(k,q,m2,m4)
        tot+=Fk*s
    return tot
dim=2**n
ann=[]
for i in range(n):
    M=np.zeros((dim,dim))
    for st in range(dim):
        if (st>>i)&1:
            sign=(-1)**bin(st & ((1<<i)-1)).count('1')
            M[st ^ (1<<i), st]=sign
    ann.append(M)
cre=[a.T for a in ann]
idx=[st for st in range(dim) if bin(st).count('1')==5]
Sz=sum(s*cre[i]@ann[i] for i,(m,s) in enumerate(orbs))
Sp=sum(cre[2*a]@ann[2*a+1] for a in range(5))
Sm=sum(cre[2*a+1]@ann[2*a] for a in range(5))
S2=Sm@Sp+Sz@Sz+Sz
S2s=S2[np.ix_(idx,idx)]
def build(Dq,B,C):
    F=(0.0,49*B+7*C,63*C/5.0)
    Peg=np.zeros((5,5)); Peg[2,2]=1
    v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2)
    Peg+=np.outer(v,v)
    Vmat=-4*Dq*np.eye(5)+10*Dq*Peg
    H=np.zeros((dim,dim))
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            if s1==s2 and abs(Vmat[m1+2,m2+2])>1e-14:
                H+=Vmat[m1+2,m2+2]*cre[i]@ann[j]
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            for k,(m3,s3) in enumerate(orbs):
                if s1!=s3: continue
                for l,(m4,s4) in enumerate(orbs):
                    if s2!=s4 or i==j or k==l: continue
                    val=Vsp(m1,m2,m3,m4,F)
                    if abs(val)<1e-12: continue
                    H+=0.5*val*(cre[i]@cre[j]@ann[l]@ann[k])
    Hs=H[np.ix_(idx,idx)]
    w,U=np.linalg.eigh(Hs)
    ss=np.real(np.einsum('ia,ij,ja->a',U,S2s,U))
    return w,ss
EOF
python3 -c "
from ligf import *
w,ss=build(0,1.0,0.0)
import collections
print(collections.Counter([(round(a,3),round(b,3)) for a,b in zip(w-w.min(),ss)]))
"