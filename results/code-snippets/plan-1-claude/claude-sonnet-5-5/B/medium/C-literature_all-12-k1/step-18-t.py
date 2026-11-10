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
print('imag',abs(np.einsum('ia,jb,kc,ld,abcd->ijkl',U.conj(),U.conj(),U,U,V2).imag).max())
for G in (R2,R4):
    print(abs(G-G.transpose(2,3,0,1)).max(),abs(G-G.transpose(1,0,3,2)).max(),abs(G-G.transpose(2,1,0,3)).max(),abs(G).max())
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
T=[]
for n,d in enumerate(dets):
    for r in d:
      for t in d:
        if r==t:continue
        for p in range(10):
          for q in range(10):
            if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]:continue
            nd,sg=apply([(r,0),(t,0),(q,1),(p,1)],d)
            if nd is None:continue
            T.append((di[nd],n,so[p][0],so[q][0],so[r][0],so[t][0],sg))
T=np.array(T);ta,tb,tp,tq,tr_,tt=[T[:,i].astype(int) for i in range(6)];tsg=T[:,6]
hd=lambda Dq:np.array([sum(6*Dq if so[i][0] in(0,3) else -4*Dq for i in d) for d in dets])
def build(Dq,B,Cc):
    f4=Cc/35;f2=B+5*f4
    G=49*f2*R2+441*f4*R4
    H=np.diag(hd(Dq))
    np.add.at(H,(ta,tb),0.5*G[tp,tq,tr_,tt]*tsg)
    return H
H=build(930,970,4300);print('asym',abs(H-H.T).max())
