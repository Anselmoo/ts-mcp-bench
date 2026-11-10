import numpy as np, itertools
from scipy.linalg import expm
from sympy.physics.wigner import wigner_3j
from math import sqrt, pi

l=2; B=1.0; Cr=3660/859.0
F4=441*Cr/35.0; F2=(441*B+5*F4)/9.0
Fk={2:F2,4:F4}
ms=[-2,-1,0,1,2]
def C(k,q,m,mp):
    if m-mp!=q: return 0.0
    return float((-1)**(l-m)*(-1)**l*(2*l+1)*wigner_3j(l,k,l,-m,q,mp)*wigner_3j(l,k,l,0,0,0))
norb=10
V=np.zeros((norb,)*4)
for a,b,c,d in itertools.product(range(norb),repeat=4):
    if a%2!=c%2 or b%2!=d%2: continue
    ma,mb,mc,md=ms[a//2],ms[b//2],ms[c//2],ms[d//2]
    tot=0.0
    for k in (2,4):
        s=sum((-1)**q*C(k,q,ma,mc)*C(k,-q,mb,md) for q in range(-k,k+1))
        tot+=Fk[k]*s
    V[a,b,c,d]=tot

dets=[sum(1<<i for i in comb) for comb in itertools.combinations(range(norb),7)]
idx={d:n for n,d in enumerate(dets)}
D=len(dets)
def apply(mask,ops):
    sign=1
    for dag,i in reversed(ops):
        occ=(mask>>i)&1
        if (dag==0 and not occ) or (dag==1 and occ): return None,0
        if bin(mask&((1<<i)-1)).count('1')%2: sign=-sign
        mask^=(1<<i)
    return mask,sign
H_ee=np.zeros((D,D))
nz=[(a,b,c,d,V[a,b,c,d]) for a,b,c,d in itertools.product(range(norb),repeat=4) if abs(V[a,b,c,d])>1e-12]
for J,mJ in enumerate(dets):
    for a,b,c,d,v in nz:
        m,s=apply(mJ,[(1,a),(1,b),(0,d),(0,c)])
        if s: H_ee[idx[m],J]+=0.5*v*s
def one(i,j):
    M=np.zeros((D,D))
    for J,mJ in enumerate(dets):
        m,s=apply(mJ,[(1,i),(0,j)])
        if s: M[idx[m],J]+=s
    return M
Lz=np.zeros((D,D)); Lp=np.zeros((D,D))
for mIdx in range(5):
    for s in (0,1): Lz+=ms[mIdx]*one(2*mIdx+s,2*mIdx+s)
for mIdx in range(4):
    for s in (0,1): Lp+=sqrt(l*(l+1)-ms[mIdx]*(ms[mIdx]+1))*one(2*(mIdx+1)+s,2*mIdx+s)
Lx=(Lp+Lp.T)/2; Ly=(Lp-Lp.T)/(2j)
L2=Lx@Lx+Ly@Ly+Lz@Lz
Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
for mIdx in range(5):
    Sz+=0.5*(one(2*mIdx,2*mIdx)-one(2*mIdx+1,2*mIdx+1))
    Sp+=one(2*mIdx,2*mIdx+1)
Sx=(Sp+Sp.T)/2; Sy=(Sp-Sp.T)/(2j)
S2=Sx@Sx+Sy@Sy+Sz@Sz
Peg1=np.zeros((5,5)); Peg1[2,2]=1
v=np.zeros(5); v[0]=v[4]=1/sqrt(2)
Peg1+=np.outer(v,v)
Pop=np.zeros((D,D))
for mIdx in range(5):
    for mj in range(5):
        if abs(Peg1[mIdx,mj])<1e-14: continue
        for s in (0,1): Pop+=Peg1[mIdx,mj]*one(2*mIdx+s,2*mj+s)
print("commutators:", np.abs(H_ee@L2-L2@H_ee).max(), np.abs(H_ee@S2-S2@H_ee).max())
def rot(n,th):
    n=np.array(n,float); n/=np.linalg.norm(n)
    return expm(-1j*th*(n[0]*Lx+n[1]*Ly+n[2]*Lz))
classes={'E':(1,rot([0,0,1],0)),'C3':(8,rot([1,1,1],2*pi/3)),'C2':(3,rot([0,0,1],pi)),
         'C4':(6,rot([0,0,1],pi/2)),"C2'":(6,rot([1,1,0],pi))}
chars={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
order=['E','C3','C2','C4',"C2'"]
def levels(Dq):
    H=H_ee+10*Dq*Pop
    Hs=H+1000*S2
    ev,vecs=np.linalg.eigh((Hs+Hs.conj().T)/2)
    out=[]; i=0
    while i<D:
        j=i
        while j+1<D and abs(ev[j+1]-ev[i])<1e-6: j+=1
        V_=vecs[:,i:j+1]; P=V_@V_.conj().T; n=j-i+1
        Eav=np.real(np.trace(V_.conj().T@H@V_))/n
        Sv=np.real(np.trace(V_.conj().T@S2@V_))/n
        S=(-1+np.sqrt(1+4*Sv))/2
        chi={c:np.trace(P@classes[c][1]) for c in order}
        for g,ch in chars.items():
            mlt=sum(classes[c][0]*np.real(chi[c])*ch[k] for k,c in enumerate(order))/24
            for _ in range(int(round(mlt))): out.append((Eav,S,g))
        i=j+1
    return sorted(out,key=lambda x:x[0])
def lab(S,g): return f"{int(round(2*S+1))}{g}g"
if __name__=="__main__":
    for Dq in np.arange(0,4.01,0.5):
        lv=levels(Dq); E0=lv[0][0]
        print(f"Dq={Dq:.1f}:", [(lab(S,g), round(E-E0,4)) for E,S,g in lv[:8]])
