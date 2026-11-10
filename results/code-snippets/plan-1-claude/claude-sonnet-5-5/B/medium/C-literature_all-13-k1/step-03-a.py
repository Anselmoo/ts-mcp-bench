import numpy as np, itertools
from math import pi,sqrt
x,w=np.polynomial.legendre.leggauss(40); ph=np.arange(80)*2*pi/80
X,P=np.meshgrid(x,ph,indexing='ij'); W=np.outer(w,np.ones(80))*2*pi/80
st=np.sqrt(1-X**2)
def Y(l,m):
    if l==2:
        d={0:np.sqrt(5/(16*pi))*(3*X**2-1),1:-np.sqrt(15/(8*pi))*X*st*np.exp(1j*P),2:np.sqrt(15/(32*pi))*st**2*np.exp(2j*P)}
    elif l==4:
        d={0:3/16*np.sqrt(1/pi)*(35*X**4-30*X**2+3),1:-3/8*np.sqrt(5/pi)*st*X*(7*X**2-3)*np.exp(1j*P),
           2:3/8*np.sqrt(5/(2*pi))*st**2*(7*X**2-1)*np.exp(2j*P),3:-3/8*np.sqrt(35/pi)*st**3*X*np.exp(3j*P),4:3/16*np.sqrt(35/(2*pi))*st**4*np.exp(4j*P)}
    if m>=0: return d[m]
    return (-1)**m*np.conj(d[-m])
ms=range(-2,3)
def integ(f): return np.sum(W*f)
G={}
for k,F in ((2,0),(4,1)):
    for q in range(-k,k+1):
        pass
def g(m1,m2,m3,m4,Fk):
    if m1+m2!=m3+m4: return 0
    t=0
    for k in (2,4):
        for q in range(-k,k+1):
            if m1-m3+q!=0 and False: pass
            b1=integ(np.conj(Y(2,m1))*np.conj(Y(k,q))*Y(2,m3))
            if abs(b1)<1e-12: continue
            b2=integ(np.conj(Y(2,m2))*Y(k,q)*Y(2,m4))
            t+=Fk[k]*4*pi/(2*k+1)*b1*b2
    return t
cache={}
def gg(a,b,c,d,Fk):
    key=(a,b,c,d)
    if key not in cache: cache[key]=(g(a,b,c,d,{2:1,4:0}),g(a,b,c,d,{2:0,4:1}))
    return cache[key][0]*Fk[2]+cache[key][1]*Fk[4]
for a in ms:
  for b in ms:
    for c in ms:
      for d in ms: gg(a,b,c,d,{2:0,4:0})
# one-body
s2=1/sqrt(2)
# basis order m=-2..2 index m+2
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
eg=[vec({0:1}),vec({2:s2,-2:s2})]
t2=[vec({2:s2,-2:-s2}),vec({1:1}),vec({-1:1})]
def hmat(Dq):
    return sum(6*Dq*np.outer(v,v.conj()) for v in eg)+sum(-4*Dq*np.outer(v,v.conj()) for v in t2)
so=[(m,s) for m in ms for s in (0,1)]
dets=[c for c in itertools.combinations(range(10),7)]
idx={d:i for i,d in enumerate(dets)}
def apply(op,det):
    # op list of (type,orb) applied right to left; returns (sign,newdet) or None
    d=list(det); sign=1
    for t,o in reversed(op):
        if t=='a':
            if o not in d: return None
            sign*=(-1)**d.index(o); d.remove(o)
        else:
            if o in d: return None
            pos=sum(1 for e in d if e<o); sign*=(-1)**pos; d.insert(pos,o)
    return sign,tuple(d)
def build(Dq,B,C):
    F={2:49*B+7*C,4:12.6*C}
    h=hmat(Dq)
    N=len(dets); H=np.zeros((N,N),complex)
    for j,det in enumerate(dets):
        for p in range(10):
            for r in range(10):
                if so[p][1]!=so[r][1]: continue
                v=h[so[p][0]+2,so[r][0]+2]
                if abs(v)<1e-14: continue
                res=apply([('c',p),('a',r)],det)
                if res: H[idx[res[1]],j]+=v*res[0]
        for p in range(10):
         for q in range(10):
          for r in range(10):
           for s in range(10):
            if so[p][1]!=so[r][1] or so[q][1]!=so[s][1]: continue
            v=gg(so[p][0],so[q][0],so[r][0],so[s][0],F)
            if abs(v)<1e-12: continue
            res=apply([('c',p),('c',q),('a',s),('a',r)],det)
            if res: H[idx[res[1]],j]+=0.5*v*res[0]
    return H
def levels(Dq,B,C):
    H=build(Dq,B,C)
    e=np.linalg.eigvalsh((H+H.conj().T)/2)
    e=np.round(e-e[0],3)
    u,c=np.unique(np.round(e,1),return_counts=True)
    return u,c
if __name__=="__main__":
    u,c=levels(900,900,3600)
    for a,b in zip(u,c): print(a,b)
