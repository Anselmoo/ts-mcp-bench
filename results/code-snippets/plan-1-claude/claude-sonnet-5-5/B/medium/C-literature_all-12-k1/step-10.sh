cat > <SANDBOX_TMP>/c.py 2>/dev/null || true
cat > /dev/shm/c.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=range(-2,3)
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
C={(k,a,b):c(k,a,b) for k in(2,4) for a in ms for b in ms}
def Vc(k):
    V=np.zeros((5,5,5,5))
    for a in ms:
     for b in ms:
      for cc in ms:
       for d in ms:
        if a+b==cc+d:
         V[a+2,b+2,cc+2,d+2]=C[(k,a,cc)]*C[(k,b,d)]*(-1)**(a-cc)
    return V
V2,V4=Vc(2),Vc(4)
s=1/np.sqrt(2)
U=np.zeros((5,5),complex)
i_=lambda m:m+2
U[0,i_(0)]=1
U[1,i_(1)]=s;U[1,i_(-1)]=-s
U[2,i_(1)]=1j*s;U[2,i_(-1)]=1j*s
U[3,i_(2)]=s;U[3,i_(-2)]=s
U[4,i_(2)]=-1j*s;U[4,i_(-2)]=1j*s
tr=lambda V:np.einsum('ia,jb,kc,ld,abcd->ijkl',U.conj(),U.conj(),U,U,V).real
R2,R4=tr(V2),tr(V4)
so=[(o,s_) for o in range(5) for s_ in (0,1)]
dets=list(itertools.combinations(range(10),7))
di={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    det=list(det);sign=1
    for i,cr in ops:
        if cr:
            if i in det:return None,0
            pos=sum(1 for x in det if x<i);det.insert(pos,i)
        else:
            if i not in det:return None,0
            pos=det.index(i);det.pop(pos)
        sign*=(-1)**pos
    return tuple(det),sign
terms=[]
for n,d in enumerate(dets):
    for r in d:
      for t in d:
        if r==t:continue
        for p in range(10):
          for q in range(10):
            if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]:continue
            nd,sg=apply([(r,0),(t,0),(q,1),(p,1)],d)
            if nd is None:continue
            terms.append((di[nd],n,so[p][0],so[q][0],so[r][0],so[t][0],sg))
def build(Dq,B,Cc):
    f4=Cc/35;f2=B+5*f4
    G=49*f2*R2+441*f4*R4
    N=len(dets);H=np.zeros((N,N))
    for n,d in enumerate(dets):
        H[n,n]+=sum(6*Dq if so[i][0] in(0,3) else -4*Dq for i in d)
    for a,b,p,q,r,t,sg in terms:H[a,b]+=0.5*G[p,q,r,t]*sg
    return H
def lev(Dq,B,Cc):
    w=np.linalg.eigvalsh(build(Dq,B,Cc));w=w-w[0];u=[]
    for x in w:
        if not u or abs(x-u[-1][0])>0.01:u.append([x,1])
        else:u[-1][1]+=1
    return u
def q(p):
    Dq,B=p
    M=np.array([[-6*Dq,6*B],[6*B,15*B]]);e=np.linalg.eigvalsh(M)
    return [2*Dq-e[0],12*Dq-e[0],e[1]-e[0]]
r=least_squares(lambda p:np.array(q(p))-[6150,12400,16850],[800,800]);print(r.x,q(r.x))
Dq,B=r.x
for Cc in np.arange(2000,4501,500):
    print(Cc,[(round(x),n) for x,n in lev(Dq,B,Cc) if x<24000])
E
python3 /dev/shm/c.py