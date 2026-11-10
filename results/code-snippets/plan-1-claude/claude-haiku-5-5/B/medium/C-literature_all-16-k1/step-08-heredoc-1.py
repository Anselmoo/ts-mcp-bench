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
one=[];two=[]
for j,st in enumerate(states):
    for o in range(5):
        for s in range(2):
            p=2*o+s
            new,sg=apply_ops([('c',p),('a',p)],st)
            if new is not None: one.append((index[new],j,o,sg))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        for s1 in range(2):
            for s2 in range(2):
                p,q,r,s=2*a+s1,2*b+s2,2*c+s1,2*d+s2
                new,sg=apply_ops([('c',p),('c',q),('a',s),('a',r)],st)
                if new is None: continue
                two.append((index[new],j,a,b,c,d,sg))
one=np.array(one,dtype=float)
two_idx=np.array([t[:6] for t in two],dtype=int)
two_sg=np.array([t[6] for t in two],dtype=float)
def build(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    W=F2*Wk[2]+F4*Wk[4]
    O=np.einsum('ai,bj,ck,dl,ijkl->abcd',U.conj(),U.conj(),U,U,W,optimize=True)
    h=np.array([6*Dq if n in eg else -4*Dq for n in names])
    Hm=np.zeros((D,D),complex)
    np.add.at(Hm,(one[:,0].astype(int),one[:,1].astype(int)),h[one[:,2].astype(int)]*one[:,3])
    vals=O[two_idx[:,2],two_idx[:,3],two_idx[:,4],two_idx[:,5]]*two_sg*0.5
    np.add.at(Hm,(two_idx[:,0],two_idx[:,1]),vals)
    return Hm
def levels(p):
    Dq,B,C=p
    Hm=build(Dq,B,C)
    Et=np.linalg.eigvalsh(Hm[np.ix_(up,up)])
    Ef=np.linalg.eigvalsh(Hm)
    g=Et[0]
    Et=Et-g; Ef=Ef-g
    trip=np.unique(np.round(Et,4))
    rem=list(Ef)
    for e in Et:
        for _ in range(3):
            i=int(np.argmin([abs(x-e) for x in rem])); rem.pop(i)
    rem=np.sort(np.array(rem))
    return trip, rem
def res(p):
    trip,rem=levels(p)
    T2=trip[1]; T1a=trip[2]; T1b=trip[3]
    E1=rem[0]
    return np.array([T2-7400,T1a-12660,T1b-23840,E1-15150])
sol=least_squares(res,[740,950,3800],x_scale=[100,100,300])
print("Dq,B,C=",np.round(sol.x,1),"resid",np.round(sol.fun,2))
t,r=levels(sol.x); print("triplets",np.round(t,1)); print("singlets",np.round(r,1))
# also alternative Eg (upper Eg singlet)
