
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # <l m1|C^k_{m1-m2}|l m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    # Y* Y_k Y: gaunt(l,k,l,-m1,q,m2)
    return float((-1)**m1*np.sqrt(5*5)*0+ 0) if False else float((-1)**m1*gaunt(2,k,2,-m1,q,m2)*np.sqrt(5*5)*np.sqrt(4*np.pi/(2*k+1))/np.sqrt(5*5)*np.sqrt(5*5)) if False else float(gaunt(2,k,2,-m1,q,m2)*(-1)**m1*np.sqrt(4*np.pi/(2*k+1)))*(-1)**0
# orbital index i=(m), spin s ; so=2*(m+2)+s
def g(k,a,b,c,d): # <ab|g|cd> radial angular
    if a[0]+b[0]!=c[0]+d[0]: return 0
    return ck(k,a[0],c[0])*ck(k,d[0],b[0])
# real crystal field in complex basis
def cf(Dq):
    # Oh potential: Dq*(... ) via matrix: eg real orbitals z2 (m0), x2-y2 (m2,-2 sym)
    U=np.zeros((5,5),complex)
    # real basis vectors in m=-2..2 order
    s=1/np.sqrt(2)
    v={}
    v['z2']=np.array([0,0,1,0,0],complex)
    v['x2y2']=np.array([s,0,0,0,s],complex)
    v['xy']=np.array([-1j*s,0,0,0,1j*s])
    v['xz']=np.array([0,s,0,-s,0],complex)
    v['yz']=np.array([0,1j*s,0,1j*s,0])
    H=np.zeros((5,5),complex)
    for n,e in [('z2',6),('x2y2',6),('xy',-4),('xz',-4),('yz',-4)]:
        H+=e*Dq*np.outer(v[n],v[n].conj())
    return H
so=[(m,s) for m in ms for s in (0,1)]
dets=[c for c in itertools.combinations(range(10),7)]
# use Ms=1/2 only
dets=[d for d in dets if sum(so[i][1]==0 for i in d)==4]  # 4 up,3 down
idx={d:i for i,d in enumerate(dets)}
def build(B,C,Dq):
    F4=C/35;F2=B+5*F4
    Fk={0:0,2:F2,4:F4}
    # two-electron antisymmetrized: V=1/2 sum <ab|cd> a+b+ d c  
    # precompute
    N=len(dets);H=np.zeros((N,N),complex)
    h=cf(Dq)
    # coefficients
    V={}
    for a in range(10):
     for b in range(10):
      for c in range(10):
       for d in range(10):
        A,Bb,Cc,D=so[a],so[b],so[c],so[d]
        if A[1]!=Cc[1] or Bb[1]!=D[1]: continue
        val=sum(Fk[k]*g(k,A,Bb,Cc,D) for k in (2,4))
        if abs(val)>1e-12: V[(a,b,c,d)]=val
    def apply(det,ops):
        # ops list of (type,i) applied right to left; return sign, newdet
        occ=list(det);sign=1
        for t,i in reversed(ops):
            if t=='a':
                if i not in occ: return 0,None
                p=occ.index(i);sign*=(-1)**p;occ.pop(p)
            else:
                if i in occ: return 0,None
                p=sum(1 for o in occ if o<i);sign*=(-1)**p;occ.insert(p,i)
        return sign,tuple(occ)
    for dt in dets:
        j=idx[dt]
        for (a,b,c,d),val in V.items():
            sg,nd=apply(dt,[('c',a),('c',b),('a',d),('a',c)])
            if sg and nd in idx: H[idx[nd],j]+=0.5*val*sg
        for a in range(10):
         for c in range(10):
            if so[a][1]!=so[c][1]: continue
            hv=h[so[a][0]+2,so[c][0]+2]
            if abs(hv)<1e-12: continue
            sg,nd=apply(dt,[('c',a),('a',c)])
            if sg and nd in idx: H[idx[nd],j]+=hv*sg
    return np.linalg.eigvalsh(H)
def bands(B,C,Dq):
    e=build(B,C,Dq);e=np.round(e-e[0],3)
    u=[];
    for x in e:
        if not u or abs(x-u[-1][0])>0.5: u.append([x,1])
        else: u[-1][1]+=1
    return u
if __name__=="__main__":
    for x in bands(900,3200,1000)[:14]: print(x)
E
python3 /tmp/a.py