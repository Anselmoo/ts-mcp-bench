mkdir -p /tmp/ts && cat > /tmp/ts/ts.py << 'EOF'
import numpy as np, itertools
from scipy.linalg import expm, eigh
from sympy.physics.wigner import wigner_3j
from math import sqrt, pi

l=2; B=1.0; Cr=3660/859.0
F4=441*Cr/35.0; F2=(441*B+5*F4)/9.0   # Racah B=(9F2-5F4)/441, C=35F4/441
Fk={0:0.0,2:F2,4:F4}
ms=[-2,-1,0,1,2]
def C(k,q,m,mp):  # <l m|C^k_q|l mp>
    if m-mp!=q: return 0.0
    return float((-1)**(l-m)*(-1)**l*(2*l+1)*wigner_3j(l,k,l,-m,q,mp)*wigner_3j(l,k,l,0,0,0))
# spin-orbital index i = 2*mi + s
norb=10
def mi(i): return i//2
def si(i): return i%2
V=np.zeros((norb,)*4)
for a,b,c,d in itertools.product(range(norb),repeat=4):
    if si(a)!=si(c) or si(b)!=si(d): continue
    ma,mb,mc,md=ms[mi(a)],ms[mi(b)],ms[mi(c)],ms[mi(d)]
    tot=0.0
    for k in (2,4):
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*C(k,q,ma,mc)*C(k,-q,mb,md)
        tot+=Fk[k]*s
    V[a,b,c,d]=tot

# determinant basis: 7 electrons in 10 spin-orbitals
dets=[sum(1<<i for i in comb) for comb in itertools.combinations(range(norb),7)]
idx={d:n for n,d in enumerate(dets)}
def apply(mask,ops):
    sign=1
    for dag,i in reversed(ops):
        occ=(mask>>i)&1
        par=bin(mask&((1<<i)-1)).count('1')
        if dag==0:
            if not occ: return None,0
        else:
            if occ: return None,0
        if par%2: sign=-sign
        mask^=(1<<i)
    return mask,sign
D=len(dets)
H_ee=np.zeros((D,D))
nz=[(a,b,c,d,V[a,b,c,d]) for a,b,c,d in itertools.product(range(norb),repeat=4) if abs(V[a,b,c,d])>1e-12]
for J,mJ in enumerate(dets):
    for a,b,c,d,v in nz:
        m1,s1=apply(mJ,[(0,c)]) if True else (None,0)
        if s1==0: continue
        m2,s2=apply(m1,[(0,d)])
        if s2==0: continue
        m3,s3=apply(m2,[(1,b)])
        if s3==0: continue
        m4,s4=apply(m3,[(1,a)])
        if s4==0: continue
        H_ee[idx[m4],J]+=0.5*v*s1*s2*s3*s4
# one-body ops
def one(i,j):  # c^dag_i c_j matrix
    M=np.zeros((D,D))
    for J,mJ in enumerate(dets):
        m,s=apply(mJ,[(1,i),(0,j)])
        if s: M[idx[m],J]+=s
    return M
# orbital L operators (sum over spins)
Lz=np.zeros((D,D)); Lp=np.zeros((D,D))
for mIdx in range(5):
    for s in (0,1):
        Lz+=ms[mIdx]*one(2*mIdx+s,2*mIdx+s)
for mIdx in range(4):
    for s in (0,1):
        Lp+=sqrt(l*(l+1)-ms[mIdx]*(ms[mIdx]+1))*one(2*(mIdx+1)+s,2*mIdx+s)
Lx=(Lp+Lp.T)/2; Ly=(Lp-Lp.T)/(2j)
L2=Lx@Lx+Ly@Ly+Lz@Lz
# spin operators
Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
for mIdx in range(5):
    Sz+=0.5*(one(2*mIdx,2*mIdx)-one(2*mIdx+1,2*mIdx+1))
    Sp+=one(2*mIdx,2*mIdx+1)
Sx=(Sp+Sp.T)/2; Sy=(Sp-Sp.T)/(2j)
S2=Sx@Sx+Sy@Sy+Sz@Sz
# crystal field: eg projector in m basis (dz2 = m0 ; dx2-y2 = (m2+m-2)/sqrt2)
Peg1=np.zeros((5,5))
Peg1[2,2]=1
v=np.zeros(5); v[0]=1/sqrt(2); v[4]=1/sqrt(2)
Peg1+=np.outer(v,v)
Pop=np.zeros((D,D))
for mIdx in range(5):
    for mj in range(5):
        if Peg1[mIdx,mj]==0: continue
        for s in (0,1):
            Pop+=Peg1[mIdx,mj]*one(2*mIdx+s,2*mj+s)
# Oh: eg at +6Dq, t2g at -4Dq -> 10Dq*P_eg (+const)
print("check [H_ee,L2]:", np.abs(H_ee@L2-L2@H_ee).max(), " [H_ee,S2]:", np.abs(H_ee@S2-S2@H_ee).max())
# free-ion check
w=np.linalg.eigvalsh(H_ee)
print("Dq=0 distinct energies (rel. to min):")
Hs0=H_ee+1000*S2
ev,vecs=eigh((Hs0+Hs0.conj().T)/2)
# class ops for O rotation group
def rot(n,th):
    n=np.array(n,float); n/=np.linalg.norm(n)
    return expm(-1j*th*(n[0]*Lx+n[1]*Ly+n[2]*Lz))
classes={'E':(1,[rot([0,0,1],0)]),
 'C3':(8,[rot([1,1,1],2*pi/3)]),
 'C2':(3,[rot([0,0,1],pi)]),
 'C4':(6,[rot([0,0,1],pi/2)]),
 "C2'":(6,[rot([1,1,0],pi)])}
chars={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
dims={'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
order=['E','C3','C2','C4',"C2'"]
Us={c:classes[c][1][0] for c in order}
Ssum=None
def levels(Dq):
    H=H_ee+10*Dq*Pop
    Hs=H+1000*S2
    ev,vecs=eigh((Hs+Hs.conj().T)/2)
    out=[]
    # cluster
    i=0
    while i<D:
        j=i
        while j+1<D and abs(ev[j+1]-ev[i])<1e-6: j+=1
        V_=vecs[:,i:j+1]
        P=V_@V_.conj().T
        Eav=np.real(np.trace(V_.conj().T@H@V_))/(j-i+1)
        Sv=np.real(np.trace(V_.conj().T@S2@V_))/(j-i+1)
        S=(-1+np.sqrt(1+4*Sv))/2
        # characters
        chi={c:np.trace(P@Us[c]) for c in order}
        mult={}
        for g,ch in chars.items():
            n=sum(classes[c][0]*np.real(chi[c])*ch[k] for k,c in enumerate(order))/24
            mult[g]=int(round(n))
        for g,nm in mult.items():
            for _ in range(nm):
                out.append((Eav,S,g))
        i=j+1
    return out
def label(S,g):
    return f"{int(round(2*S+1))}{g}" + ("g")
if __name__=="__main__":
    import sys
    for Dq in np.arange(0,4.01,0.5):
        lv=levels(Dq)
        lv=sorted(lv,key=lambda x:x[0])
        E0=lv[0][0]
        print(f"Dq={Dq:.1f}: ", [ (label(S,g), round(E-E0,4)) for E,S,g in lv[:8]])
EOF
cd /tmp/ts && <B_VENV>/bin/python3 ts.py