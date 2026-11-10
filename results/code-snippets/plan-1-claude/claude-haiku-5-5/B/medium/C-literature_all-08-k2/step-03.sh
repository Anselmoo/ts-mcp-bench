mkdir -p /tmp/lf && cat > /tmp/lf/d5.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi
# spin-orbitals: idx = 2*(m+2)+s, s=0 up, 1 down
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
N=10
# angular coefficients A[k][m1,m2,m3,m4] for <m1 m2|1/r12|m3 m4>, per unit F^k
A={}
for k in (0,2,4):
    arr=np.zeros((5,5,5,5))
    for i1,m1 in enumerate(range(-2,3)):
     for i2,m2 in enumerate(range(-2,3)):
      for i3,m3 in enumerate(range(-2,3)):
       for i4,m4 in enumerate(range(-2,3)):
        tot=0.0
        for q in range(-k,k+1):
            if abs(-m1-q+m3)>0 and False: pass
            g1=float(gaunt(2,k,2,-m1,-q,m3)) if abs(-m1-q)<=0 or True else 0
            if (-m1)-q+m3!=0 or abs(q)>k: continue
            if (-m2)+q+m4!=0: continue
            g1=float(gaunt(2,k,2,-m1,-q,m3)); g2=float(gaunt(2,k,2,-m2,q,m4))
            tot+=(-1)**(m1+q+m2)*g1*g2
        arr[i1,i2,i3,i4]=4*pi/(2*k+1)*tot
    A[k]=arr
# Slater-Condon two-electron integral <ab|cd> for spin-orbitals (spin delta)
def V(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd: return 0.0
    tot=0.0
    for k in (0,2,4):
        tot+=F[k]*A[k][ma+2,mb+2,mc+2,md+2]
    return tot
# basis: 5 electrons in 10 spin-orbitals
basis=[]
for occ in itertools.combinations(range(10),5):
    basis.append(occ)
idx={s:i for i,s in enumerate(basis)}
def build(Dq,B,C):
    F={0:0.0,2:441*B+63*C,4:12.6*C}
    # h: cubic field in complex basis. eg: z2 (m=0), x2-y2 (m=±2 combo); t2g: xz,yz (m=±1), xy (m=±2 combo)
    h1=np.zeros((10,10),complex)
    # real-orbital projectors in m space (5x5)
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[m+2]=c
        return v
    s2=np.sqrt(2)
    orbitals={
     'z2':(6,vec({0:1})),
     'x2y2':(6,vec({2:1/s2,-2:1/s2})),
     'xy':(-4,vec({2:1/(1j*s2),-2:-1/(1j*s2)})),
     'xz':(-4,vec({1:1/s2,-1:-1/s2})),
     'yz':(-4,vec({1:1/(1j*s2),-1:1/(1j*s2)})),
    }
    M=np.zeros((5,5),complex)
    for name,(e,v) in orbitals.items():
        M+=Dq*e*np.outer(v,v.conj())
    for i,(m,s) in enumerate(orbs):
        for j,(mm,ss) in enumerate(orbs):
            if s==ss: h1[i,j]=M[m+2,mm+2]
    # build H
    dim=len(basis)
    H=np.zeros((dim,dim))
    Hc=np.zeros((dim,dim),complex)
    # precompute V tensor
    Vt=np.zeros((10,10,10,10))
    for a in range(10):
     for b in range(10):
      for c in range(10):
       for d in range(10):
        Vt[a,b,c,d]=V(a,b,c,d,F)
    for col,occ in enumerate(basis):
        occset=list(occ)
        # one-body
        for i in range(10):
          for j in range(10):
            if h1[i,j]==0: continue
            if j not in occset: continue
            new=set(occset); new.remove(j)
            if i in new: continue
            sign=1
            # sign for a_i^dag a_j
            lst=sorted(occset); pj=lst.index(j)
            s=(-1)**pj
            newl=sorted((new|{i})); pi_=newl.index(i)
            s*=(-1)**pi_
            row=idx[tuple(newl)]
            Hc[row,col]+=s*h1[i,j]
        # two-body: 1/2 sum V_ijkl a_i^+ a_j^+ a_l a_k  with <ij|kl>
        for k_ in occset:
          for l_ in occset:
            if k_==l_: continue
            for i in range(10):
              for j in range(10):
                v=Vt[i,j,k_,l_]
                if v==0 or i==j: continue
                new=set(occset)
                # annihilate l then k (apply a_k first: a_l a_k |occ>, we do k then l)
                # sign computed sequentially
                st=list(occset); sgn=1
                # a_k
                p=st.index(k_); sgn*=(-1)**p; st.remove(k_)
                # a_l
                p=st.index(l_); sgn*=(-1)**p; st.remove(l_)
                # a_j^+
                if j in st: continue
                p=sum(1 for x in st if x<j); sgn*=(-1)**p; st.append(j); st.sort()
                # a_i^+
                if i in st: continue
                p=sum(1 for x in st if x<i); sgn*=(-1)**p; st.append(i); st.sort()
                row=idx[tuple(st)]
                Hc[row,col]+=0.5*sgn*v
    return Hc
# S^2 operator in this basis
def S2(): 
    Sz=np.zeros((len(basis),)*2)
    return None
if __name__=='__main__':
    H=build(0.0,1.0,4.0)
    ev=np.linalg.eigvalsh((H+H.conj().T)/2)
    print(np.round(np.unique(np.round(ev,6)),4))
EOF
cd /tmp/lf && time python3 d5.py