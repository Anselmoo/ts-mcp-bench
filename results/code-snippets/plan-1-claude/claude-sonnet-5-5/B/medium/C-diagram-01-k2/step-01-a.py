import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=828.;C=3390.
F4=C/35;F2=B+5*F4  # F2,F4 in units where F^k = F_k * D
# actual F^2=49F2, F^4=441F4
Fk={0:0,2:49*F2,4:441*F4}
# note: B=F2-5F4 (reduced) check
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <l m1|C^k_{m1-m2}|l m2> *
    return float(gaunt(2,k,2,-m1,m1-m2,m2)*(-1)**m1*5) if True else 0
def V(m1,m2,m3,m4): # <m1 m2|g|m3 m4>
    if m1+m2!=m3+m4: return 0
    s=0
    for k in (2,4):
        q=m1-m3
        s+=Fk[k]*(-1)**q*ck(k,m1,m3)*ck(k,m4,m2)*0 if False else 0
    return s
# use standard: sum_k F^k c^k(m1,m3) c^k(m4,m2), c^k(m,m')=sqrt(4pi/(2k+1))(-1)^m <Y2m|Yk m-m'|Y2m'> ; use Gaunt
def c(k,m,mp):
    return float((-1)**m*np.sqrt(5*5)*gaunt(2,k,2,-m,m-mp,mp)) * (1 if True else 0)
def Vc(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return sum(Fk[k]*c(k,m1,m3)*c(k,m4,m2)/ (1) for k in (2,4))
# normalization check later via B
G=np.zeros((5,)*4)
for a in itertools.product(range(5),repeat=4):
    G[a]=Vc(*[ms[i] for i in a])
# real orbitals order: xy, yz, z2, xz, x2-y2  as combos of complex m
s2=1/np.sqrt(2)
U=np.zeros((5,5),complex) # real_i = sum_m U[i,m] |m>
idx={m:i for i,m in enumerate(ms)}
U[0,idx[-2]]=1j*s2;U[0,idx[2]]=-1j*s2   # xy
U[1,idx[-1]]=1j*s2;U[1,idx[1]]=1j*s2    # yz
U[2,idx[0]]=1
U[3,idx[-1]]=s2;U[3,idx[1]]=-s2         # xz
U[4,idx[-2]]=s2;U[4,idx[2]]=s2          # x2-y2
Gr=np.einsum('ia,jb,kc,ld,abcd->ijkl',U.conj(),U.conj(),U,U,G)
# check: <ab|g|cd> with a,b bra conj ; Gr[i,j,k,l]=<ij|g|kl>
Gr=Gr.real if abs(Gr.imag).max()<1e-8 else Gr
print(abs(Gr.imag).max() if np.iscomplexobj(Gr) else 0)
# determinant basis Ms=1/2: spin orbitals index 2*i+s (s0 up,1 down)
dets=[d for d in itertools.combinations(range(10),3) if sum(1-(o%2)*2 for o in d)==1]
di={d:i for i,d in enumerate(dets)}
def apply_ops(ops,d): # ops list of (idx,create?) applied right to left
    d=list(d);sign=1
    for o,cr in reversed(ops):
        if cr:
            if o in d: return 0,None
            pos=sum(1 for x in d if x<o); d.insert(pos,o); sign*=(-1)**pos
        else:
            if o not in d: return 0,None
            pos=d.index(o); d.pop(pos); sign*=(-1)**pos
    return sign,tuple(d)
def ham(Dq):
    n=len(dets);H=np.zeros((n,n))
    h=np.diag([-4,-4,6,-4,6])*Dq  # xy,yz,z2,xz,x2y2
    h=np.diag([-4*Dq,-4*Dq,6*Dq,-4*Dq,6*Dq])
    for j,d in enumerate(dets):
        for p in range(5):
            for s in (0,1):
                sg,nd=apply_ops([(2*p+s,1),(2*p+s,0)],d)
                if sg: H[di[nd],j]+=sg*h[p,p]
        for i in range(5):
          for jj in range(5):
            for k in range(5):
              for l in range(5):
                g=Gr[i,jj,k,l]
                if abs(g)<1e-9: continue
                for s in (0,1):
                  for t in (0,1):
                    sg,nd=apply_ops([(2*i+s,1),(2*jj+t,1),(2*l+t,0),(2*k+s,0)],d)
                    if sg: H[di[nd],j]+=0.5*g*sg
    return H
def rot(perm):  # perm: orbital -> (orbital,sign)
    n=len(dets);R=np.zeros((n,n))
    for j,d in enumerate(dets):
        sg=1;new=[]
        for o in d:
            p,s=perm[o//2]; sg*=s; new.append(2*p+o%2)
        # sort sign
        sgn=1
        for a in range(3):
            for b in range(a+1,3):
                if new[a]>new[b]: sgn=-sgn
        R[di[tuple(sorted(new))],j]+=sg*sgn
    return R
# orbitals 0 xy,1 yz,2 z2,3 xz,4 x2y2
C4=rot({0:(0,-1),1:(3,1),2:(2,1),3:(1,-1),4:(4,-1)}) # x->y,y->-x: yz->xz... 
C2p=rot({0:(0,1),1:(3,-1),2:(2,1),3:(1,-1),4:(4,-1)})
# S2
def S2():
    n=len(dets);M=np.zeros((n,n))
    for j,d in enumerate(dets):
        sz=0.5
        M[j,j]+=sz*sz+sz*0  # Sz^2 + Sz
        M[j,j]+=sz
        # S- S+ : S+ then S-
        for p in range(5):
            for q in range(5):
                # S-S+ = sum_{p,q} a†_{p dn}... S+=sum p a†_{p up}a_{p dn}; S-=sum a†_{q dn}a_{q up}
                sg,nd=apply_ops([(2*q+1,1),(2*q,0),(2*p,1),(2*p+1,0)],d)
                if sg: M[di[nd],j]+=sg
    return M
S=S2()
def run(Dq):
    H=ham(Dq)
    w,v=np.linalg.eigh(H+1e-3*S)  # separate spin
    return H,w,v
if __name__=="__main__":
    H=ham(0.0);print(np.linalg.eigvalsh(H)[:3]); print(np.round(np.linalg.eigvalsh(S)[:3],3))
