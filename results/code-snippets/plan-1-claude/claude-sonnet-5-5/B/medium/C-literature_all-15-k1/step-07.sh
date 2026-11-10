mkdir -p <SANDBOX_TMP> && cd <SANDBOX_TMP> && cat > d7.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2; ms=range(-2,3)
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*5*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m1,q,m2))
CK={k:{(a,b):ck(k,a,b) for a in ms for b in ms} for k in (2,4)}
so=[(m,s) for m in ms for s in (0,1)]
n=10
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(n),7)]
sz=np.array([ (sum((d>>i)&1 for i in range(0,n,2))-sum((d>>i)&1 for i in range(1,n,2)))/2 for d in dets])
def apply(op,d):
    sign=1
    for t,i in reversed(op):
        occ=(d>>i)&1
        if t=='a' and not occ: return 0,0
        if t=='c' and occ: return 0,0
        sign*= (-1)**bin(d&((1<<i)-1)).count('1')
        d^=1<<i
    return sign,d
# precompute g structure (without Fk): g2,g4
G={k:np.zeros((n,n,n,n)) for k in (2,4)}
for a,(m1,s1) in enumerate(so):
 for b,(m2,s2) in enumerate(so):
  for c,(m3,s3) in enumerate(so):
   for e,(m4,s4) in enumerate(so):
    if s1==s3 and s2==s4 and m1+m2==m3+m4:
     for k in (2,4): G[k][a,b,c,e]=CK[k][(m1,m3)]*CK[k][(m4,m2)]
def mats(sel):
    ds=[dets[i] for i in sel]; ix={d:i for i,d in enumerate(ds)}; N=len(ds)
    M={'cf':np.zeros((N,N)),2:np.zeros((N,N)),4:np.zeros((N,N))}
    hv={2:1,1:-4,0:6,-1:-4,-2:1}
    h=np.zeros((n,n))
    for s in (0,1):
        for m in ms: h[so.index((m,s)),so.index((m,s))]=hv[m]
        h[so.index((2,s)),so.index((-2,s))]=5; h[so.index((-2,s)),so.index((2,s))]=5
    for j,d in enumerate(ds):
        for i1 in range(n):
          for i2 in range(n):
            if h[i1,i2]:
              s,d2=apply([('c',i1),('a',i2)],d)
              if s: M['cf'][ix[d2],j]+=s*h[i1,i2]
        for k in (2,4):
         for a,b,c,e in zip(*np.nonzero(G[k])):
              s,d2=apply([('c',a),('c',b),('a',e),('a',c)],d)
              if s: M[k][ix[d2],j]+=0.5*s*G[k][a,b,c,e]
    return M
Mq=mats(np.where(sz==1.5)[0]); Md=mats(np.where(sz==0.5)[0])
def lv(Dq,B,C):
    F2=B+C/7;F4=C/35
    out={}
    for name,M in (('q',Mq),('d',Md)):
        H=Dq*M['cf']+49*F2*M[2]+441*F4*M[4]
        out[name]=np.linalg.eigvalsh(H)
    return out
def groups(w,tol=1e-3):
    g=[]
    for x in w:
        if g and abs(x-g[-1][0])<tol: g[-1][1]+=1
        else: g.append([x,1])
    return g
if __name__=="__main__":
    o=lv(900,800,3500); e0=o['q'][0]
    for nm in 'qd': print(nm,[(round(x-e0),c) for x,c in groups(o[nm])][:14])
E
python3 d7.py