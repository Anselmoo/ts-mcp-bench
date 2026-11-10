
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    g=float(gaunt(2,k,2,-m1,q,m2))*(-1)**m1
    return np.sqrt(4*np.pi/(2*k+1))*g
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
orbs=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),6))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply(ops,det):
    det=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in det: return 0,None
            p=det.index(o);sign*=(-1)**p;det.pop(p)
        else:
            if o in det: return 0,None
            p=sum(1 for x in det if x<o);sign*=(-1)**p;det.insert(p,o)
    return sign,tuple(det)
def g2(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.0
    return sum(CK[(k,ma,mc)]*CK[(k,md,mb)]*F[k] for k in (2,4))
def Hee(F):
    Hm=np.zeros((N,N))
    for j,d in enumerate(dets):
        for a in range(10):
          for b in range(10):
            if a==b: continue
            for c in d:
              for e in d:
                if c==e: continue
                val=g2(a,b,c,e,F)
                if val==0: continue
                s,nd=apply([('c',a),('c',b),('a',e),('a',c)],d)
                if s: Hm[idx[nd],j]+=0.5*s*val
    return Hm
def op1(f):
    M=np.zeros((N,N))
    for j,d in enumerate(dets):
        for p,q,v in f:
            s,nd=apply([('c',p),('a',q)],d)
            if s: M[idx[nd],j]+=s*v
    return M
Vd={2:1,1:-4,0:6}
f=[]
for i,m in enumerate(ms):
    for s in (0,1):
        f.append((2*i+s,2*i+s,Vd[abs(m)]))
for s in (0,1):
    f.append((s,8+s,5));f.append((8+s,s,5))
HD=op1(f)
HB=Hee({2:49,4:0})
HC=Hee({2:7,4:441/35})
Sp=op1([(2*i,2*i+1,1.0) for i in range(5)])
Szd=np.array([sum(0.5 if orbs[o][1]==0 else -0.5 for o in d) for d in dets])
Sz=np.diag(Szd)
S2=Sp.T@Sp+Sz@Sz+Sz
# restrict to Sz=0
sel=np.where(Szd==0)[0]
def singlets(Dq,B,C):
    H=(Dq*HD+B*HB+C*HC)[np.ix_(sel,sel)]
    S=S2[np.ix_(sel,sel)]
    Hs=H+1e6*S  # push non-singlets up
    w=np.linalg.eigvalsh(Hs)
    w=w[w<5e5]
    return w-w[0]
def levels(Dq,B,C):
    H=(Dq*HD+B*HB+C*HC)[np.ix_(sel,sel)]
    S=S2[np.ix_(sel,sel)]
    w,v=np.linalg.eigh(H+1e-3*S)
    s=np.einsum('ij,ij->j',v,S@v)
    return w,s
e=singlets(1643,548.75,4.5*548.75)
# group degeneracies
def grp(e):
    out=[];
    for x in e:
        if out and abs(x-out[-1][0])<1: out[-1][1]+=1
        else: out.append([x,1])
    return out
print(grp(e)[:8])
obs=np.array([13960,22740,29700])
def res(p):
    g=grp(singlets(p[0],p[1],4.5*p[1]))
    return np.array([g[1][0],g[2][0],g[3][0]])-obs
r=least_squares(res,[1643,548]); print(r.x,res(r.x),grp(singlets(r.x[0],r.x[1],4.5*r.x[1]))[:6])
w,s=levels(r.x[0],r.x[1],4.5*r.x[1]); print(grp(w-w[0])[:6], s[:3])
EOF
