import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
import scipy.sparse as sp
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=48
ph=np.arange(nphi)*2*np.pi/nphi
TH=np.arccos(xg)
TT,PP=np.meshgrid(TH,ph,indexing='ij')
W=(np.outer(wg,np.ones(nphi))*(2*np.pi/nphi))
def Y(l,m): return sph_harm_y(l,m,TT,PP)
ms=[-2,-1,0,1,2]
Yd={m:Y(2,m) for m in ms}
def C(k,q,a,c):
    if abs(q)>k: return 0.0
    f=np.sqrt(4*np.pi/(2*k+1))
    return np.sum(W*np.conj(Yd[a])*f*Y(k,q)*Yd[c])
A={}
for k in (0,2,4):
    for a in ms:
     for c in ms:
      for b in ms:
       for d in ms:
        A[(k,a,b,c,d)]=sum(((-1)**q)*C(k,q,a,c)*C(k,-q,b,d) for q in range(-k,k+1))
so=[(m,s) for m in ms for s in (0,1)]   # index = 2*(m+2)+s
n=10
def Vtensor(F2,F4):
    F={0:0.0,2:F2,4:F4}
    V=np.zeros((n,n,n,n))
    for i,(ma,sa) in enumerate(so):
     for j,(mb,sb) in enumerate(so):
      for k,(mc,sc) in enumerate(so):
       for l,(md,sd) in enumerate(so):
        if sa==sc and sb==sd:
          V[i,j,k,l]=sum(F[kk]*A[(kk,ma,mb,mc,md)].real for kk in (0,2,4))
    return V
# determinant basis, 3 electrons
dets=list(itertools.combinations(range(n),3))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(ops,occ):
    # ops: list of ('c' or 'a', p) applied right-to-left as given in list order (last applied first)
    st=list(occ); sign=1
    for typ,p in reversed(ops):
        if typ=='a':
            if p not in st: return None,0
            pos=st.index(p); sign*= (-1)**pos; st.pop(pos)
        else:
            if p in st: return None,0
            pos=sum(1 for x in st if x<p); sign*=(-1)**pos; st.insert(pos,p)
    return tuple(st),sign
def build(Dq,B,Cc):
    F4=7*Cc/5; F2=49*B+7*Cc
    V=Vtensor(F2,F4)
    # one-body
    P_t=np.zeros((5,5)); P_e=np.zeros((5,5))
    id_={m:i for i,m in enumerate(ms)}
    P_t[id_[1],id_[1]]=1; P_t[id_[-1],id_[-1]]=1
    va=np.zeros(5); va[id_[2]]=1/np.sqrt(2); va[id_[-2]]=-1/np.sqrt(2)
    vb=np.zeros(5); vb[id_[2]]=1/np.sqrt(2); vb[id_[-2]]=1/np.sqrt(2)
    P_t+=np.outer(va,va); P_e[id_[0],id_[0]]=1; P_e+=np.outer(vb,vb)
    Vf=-4*Dq*P_t+6*Dq*P_e
    h=np.zeros((n,n))
    for i,(m,s) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s==s2: h[i,j]=Vf[id_[m],id_[m2]]
    D=len(dets); H=np.zeros((D,D))
    for x,occ in enumerate(dets):
        for y,ket in enumerate(dets):
            tot=0.0
            # one-body c†_i c_j
            for i in range(n):
                for j in range(n):
                    if abs(h[i,j])<1e-14: continue
                    st,sg=apply_ops([('c',i),('a',j)],ket)
                    if st is not None and st==occ: tot+=h[i,j]*sg
            # two-body 1/2 V_ijkl c†_i c†_j c_l c_k
            for i in range(n):
             for j in range(n):
              for k in range(n):
               for l in range(n):
                v=V[i,j,k,l]
                if abs(v)<1e-14: continue
                st,sg=apply_ops([('c',i),('c',j),('a',l),('a',k)],ket)
                if st is not None and st==occ: tot+=0.5*v*sg
            H[x,y]=tot
    return H
if __name__=="__main__":
    import sys
    H=build(0,0,0)
    print(np.round(np.linalg.eigvalsh(H),6))
