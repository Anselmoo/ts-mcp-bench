cat > /tmp/fit_in.py << 'EOF'
PLACEHOLDER
EOF
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache
from scipy.optimize import least_squares
l=2; ms=list(range(-2,3))
def idx(m): return m+2
@lru_cache(None)
def ang(k,m,q,mp):
    if abs(q)>k or abs(m)>l or abs(mp)>l: return 0.0
    return ((-1)**m)*np.sqrt(4*np.pi/(2*k+1))*float(gaunt(l,k,l,-m,q,mp))
Wk={k:np.zeros((5,5,5,5)) for k in (2,4)}
for k in (2,4):
    for m1,m2,m3,m4 in itertools.product(ms,ms,ms,ms):
        s=0.0
        for q in range(-k,k+1):
            s+=((-1)**q)*ang(k,m1,q,m3)*ang(k,m2,-q,m4)
        Wk[k][idx(m1),idx(m2),idx(m3),idx(m4)]=s
r2=1/np.sqrt(2); orb={}
v=np.zeros(5,complex); v[idx(0)]=1; orb['z2']=v
v=np.zeros(5,complex); v[idx(2)]=r2; v[idx(-2)]=r2; orb['x2y2']=v
v=np.zeros(5,complex); v[idx(2)]=r2; v[idx(-2)]=-r2; orb['xy']=v/1j
v=np.zeros(5,complex); v[idx(1)]=-r2; v[idx(-1)]=r2; orb['xz']=v
v=np.zeros(5,complex); v[idx(1)]=1j*r2; v[idx(-1)]=1j*r2; orb['yz']=v
names=['z2','x2y2','xy','xz','yz']
U=np.array([orb[n] for n in names])
eg={'z2','x2y2'}
def apply_ops(ops,st):
    occ=list(st); sign=1
    for t,p in reversed(ops):
        if t=='a':
            if p not in occ: return None,0
            pos=occ.index(p); sign*=(-1)**pos; occ.pop(pos)
        else:
            if p in occ: return None,0
            pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
    return tuple(occ),sign
no=10
states=list(itertools.combinations(range(no),8))
index={s:i for i,s in enumerate(states)}; D=len(states)
up=[i for i,s in enumerate(states) if sum(1 for x in s if x%2==0)==5]
# precompute operator lists
ops2=[]
for j,st in enumerate(states):
    pass
def build(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    W=F2*Wk[2]+F4*Wk[4]
    O=np.einsum('ai,bj,ck,dl,ijkl->abcd',U.conj(),U.conj(),U,U,W,optimize=True)
    h=[6*Dq if n in eg else -4*Dq for n in names]
    Hm=np.zeros((D,D),complex)
    for j,st in enumerate(states):
        for o in range(5):
            for s in range(2):
                p=2*o+s
                new,sg=apply_ops([('c',p),('a',p)],st)
                if new is not None: Hm[index[new],j]+=h[o]*sg
        for a,b,c,d in itertools.product(range(5),repeat=4):
            if abs(O[a,b,c,d])<1e-12: continue
            for s1 in range(2):
                for s2 in range(2):
                    p,q,r,s=2*a+s1,2*b+s2,2*c+s1,2*d+s2
                    new,sg=apply_ops([('c',p),('c',q),('a',s),('a',r)],st)
                    if new is None: continue
                    Hm[index[new],j]+=0.5*O[a,b,c,d]*sg
    Hup=Hm[np.ix_(up,up)]
    return np.linalg.eigvalsh(Hup), np.linalg.eigvalsh(Hm)
Et,Ef=build(1000,1000,4000)
print(np.round(Et,1))
# remove triplet eigenvalues from full spectrum
rem=list(Ef)
for e in Et:
    i=int(np.argmin([abs(x-e) for x in rem])); rem.pop(i)
rem=np.array(rem)
print("singlets:",np.round(rem,1))
np.save if False else None
import pickle
pickle.dump(None,open('/dev/null','wb'))
# fit function
def model(p):
    Dq,B,C=p
    Et,Ef=build(Dq,B,C)
    t=np.sort(Et)-np.sort(Et)[0]
    rem=list(Ef)
    for e in Et:
        i=int(np.argmin([abs(x-e) for x in rem])); rem.pop(i)
    rem=np.sort(np.array(rem))-np.sort(Et)[0]
    return t, rem
np.set_printoptions(linewidth=150)
import sys
obs={'3T2':7400,'3T1F':12660,'3T1P':23840,'1Eg':15150}
def resid(p, which):
    t,rem=model(p)
    # triplets: t = [0, 10Dq, T1a x3 (distinct), T1b]
    tl=np.unique(np.round(t,3))
    T2=tl[1]; T1a=tl[2]; T1b=tl[3]
    s=rem
    # singlet Eg candidates: pick by which
    return None
EOF