mkdir -p <SANDBOX_TMP> && cd <SANDBOX_TMP> && cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache
ms=[-2,-1,0,1,2]
@lru_cache(None)
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float(gaunt(2,k,2,-m1,q,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
def g(k,a,b,c,d):
    if a[0]+b[0]!=c[0]+d[0]: return 0
    return ck(k,a[0],c[0])*ck(k,d[0],b[0])
s=1/np.sqrt(2)
vv={'z2':[0,0,1,0,0],'x2y2':[s,0,0,0,s],'xy':[-1j*s,0,0,0,1j*s],'xz':[0,s,0,-s,0],'yz':[0,1j*s,0,1j*s,0]}
def cf(Dq):
    H=np.zeros((5,5),complex)
    for n,e in [('z2',6),('x2y2',6),('xy',-4),('xz',-4),('yz',-4)]:
        v=np.array(vv[n],complex);H+=e*Dq*np.outer(v,v.conj())
    return H
so=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),7) if sum(so[i][1]==0 for i in d)==4]
idx={d:i for i,d in enumerate(dets)}
def apply(det,ops):
    occ=list(det);sign=1
    for t,i in reversed(ops):
        if t=='a':
            if i not in occ: return 0,None
            p=occ.index(i);sign*=(-1)**p;occ.pop(p)
        else:
            if i in occ: return 0,None
            p=sum(1 for o in occ if o<i);sign*=(-1)**p;occ.insert(p,i)
    return sign,tuple(occ)
# precompute structure
def Vlist():
    L=[]
    for a in range(10):
     for b in range(10):
      for c in range(10):
       for d in range(10):
        A,Bb,Cc,D=so[a],so[b],so[c],so[d]
        if A[1]!=Cc[1] or Bb[1]!=D[1]: continue
        v2=g(2,A,Bb,Cc,D);v4=g(4,A,Bb,Cc,D)
        if abs(v2)>1e-12 or abs(v4)>1e-12: L.append((a,b,c,d,v2,v4))
    return L
VL=Vlist()
N=len(dets)
H2=np.zeros((N,N),complex);H4=np.zeros((N,N),complex)
for dt in dets:
    j=idx[dt]
    for a,b,c,d,v2,v4 in VL:
        sg,nd=apply(dt,[('c',a),('c',b),('a',d),('a',c)])
        if sg and nd in idx:
            H2[idx[nd],j]+=0.5*v2*sg;H4[idx[nd],j]+=0.5*v4*sg
H1=np.zeros((N,N),complex)
h=cf(1.0)
for dt in dets:
    j=idx[dt]
    for a in range(10):
     for c in range(10):
        if so[a][1]!=so[c][1]: continue
        hv=h[so[a][0]+2,so[c][0]+2]
        if abs(hv)<1e-12: continue
        sg,nd=apply(dt,[('c',a),('c',c)][:0]+[('c',a),('a',c)])
        if sg and nd in idx: H1[idx[nd],j]+=hv*sg
def levels(B,C,Dq):
    F4=C/35;F2=B+5*F4
    e=np.linalg.eigvalsh(F2*H2+F4*H4+Dq*H1);e=e-e[0]
    u=[]
    for x in e:
        if not u or abs(x-u[-1][0])>1: u.append([round(x),1])
        else: u[-1][1]+=1
    return u
if __name__=="__main__":
    print(levels(900,3200,1000)[:12])
E
python3 a.py