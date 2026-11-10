import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.linalg import expm, eigh
from scipy.spatial.transform import Rotation as Rot

B=1.0; C=3003/722
F2=49*B+7*C; F4=12.6*C
ms=[-2,-1,0,1,2]
# orbital ERI tensor (complex Y basis), k=2,4 parts
def Vk(k):
    T=np.zeros((5,5,5,5))
    for a,m1 in enumerate(ms):
        for b,m2 in enumerate(ms):
            for c,m3 in enumerate(ms):
                for d,m4 in enumerate(ms):
                    s=0.0
                    for q in range(-k,k+1):
                        if abs(q)>2: continue
                        g1=gaunt(2,k,2,-m1,-q,m3)
                        if g1==0: continue
                        g2=gaunt(2,k,2,-m2,q,m4)
                        s+= float((-1)**(m1+q))*float(g1)*float((-1)**m2)*float(g2)
                    T[a,b,c,d]=s*4*np.pi/(2*k+1)
    return T
V2=Vk(2); V4=Vk(4)
# spin-orbital index: 2*oi+s, s=0 up, 1 down
N=10
def so(i): return i//2, i%2
def create(i,st):
    if i in st: return None
    p=sum(1 for x in st if x<i)
    return ((-1)**p, tuple(sorted(st+(i,))))
def annih(i,st):
    if i not in st: return None
    p=st.index(i)
    return ((-1)**p, tuple(x for x in st if x!=i))
# build Coulomb tensor in spin-orbital basis
Vso={}
for i in range(N):
  for j in range(N):
    for k in range(N):
      for l in range(N):
        mi,si=so(i); mj,sj=so(j); mk,sk=so(k); ml,sl=so(l)
        if si!=sk or sj!=sl: continue
        v=F2*V2[mi,mj,mk,ml]+F4*V4[mi,mj,mk,ml]
        if abs(v)>1e-12: Vso[(i,j,k,l)]=v
dets=list(itertools.combinations(range(N),3))
ix={d:n for n,d in enumerate(dets)}
D=len(dets)
Hee=np.zeros((D,D))
for n,st in enumerate(dets):
    for (i,j,k,l),v in Vso.items():
        r=annih(k,st)
        if r is None: continue
        s1,st1=r
        r=annih(l,st1)
        if r is None: continue
        s2,st2=r
        r=create(j,st2)
        if r is None: continue
        s3,st3=r
        r=create(i,st3)
        if r is None: continue
        s4,st4=r
        Hee[ix[st4],n]+=0.5*v*s1*s2*s3*s4
# one-body operators
def onebody(h):
    M=np.zeros((D,D))
    for n,st in enumerate(dets):
        for i in range(N):
            for j in range(N):
                if abs(h[i,j])<1e-14: continue
                r=annih(j,st)
                if r is None: continue
                s1,st1=r
                r=create(i,st1)
                if r is None: continue
                s2,st2=r
                M[ix[st2],n]+=h[i,j]*s1*s2
    return M
# orbital projectors (complex basis)
Peg=np.zeros((5,5)); Pt2=np.zeros((5,5))
Peg[2,2]=1
v=np.zeros(5); v[0]=1/np.sqrt(2); v[4]=1/np.sqrt(2)  # (|2>+|-2>)/sqrt2 -> x2-y2
Peg+=np.outer(v,v)
Pt2=np.eye(5)-Peg
horb_cf = 6*Peg-4*Pt2   # coefficient of Dq
hcf=np.kron(horb_cf,np.eye(2))
Hcf=onebody(hcf)
# S+ 
hsp=np.zeros((N,N))
for oi in range(5): hsp[2*oi,2*oi+1]=1.0
Sp=onebody(hsp)
Sm=Sp.T
Sz=np.diag([sum((0.5 if st_s==0 else -0.5) for st_s in [so(x)[1] for x in st]) for st in dets])
S2=Sm@Sp+Sz@Sz+Sz
# rotation matrices for l=2
Lz=np.diag(ms).astype(complex)
Lp=np.zeros((5,5),complex)
for a,m in enumerate(ms):
    if m<2: Lp[a+1,a]=np.sqrt(6-m*(m+1))
Lm=Lp.conj().T
Ly=(Lp-Lm)/(2j)
def Dl2(R):
    al,be,ga=Rot.from_matrix(R).as_euler('zyz')
    return expm(-1j*al*Lz)@expm(-1j*be*Ly)@expm(-1j*ga*Lz)
def Gamma(R):
    U=np.kron(Dl2(R),np.eye(2))
    G=np.zeros((D,D),complex)
    for n,dn in enumerate(dets):
        for m,dm in enumerate(dets):
            G[m,n]=np.linalg.det(U[np.ix_(dm,dn)])
    return G
classes=[(1,Rot.identity().as_matrix()),
 (8,Rot.from_rotvec(np.array([1,1,1])/np.sqrt(3)*2*np.pi/3).as_matrix()),
 (3,Rot.from_rotvec([0,0,np.pi]).as_matrix()),
 (6,Rot.from_rotvec([0,0,np.pi/2]).as_matrix()),
 (6,Rot.from_rotvec(np.array([1,1,0])/np.sqrt(2)*np.pi).as_matrix())]
Gs=[Gamma(R) for _,R in classes]
chartab={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
sizes=[c for c,_ in classes]
def label(Q,S):
    dimorb=Q.shape[1]//(2*S+1)
    chis=[np.trace(Q.conj().T@G@Q).real/(2*S+1) for G in Gs]
    best=None
    for name,ct in chartab.items():
        mult=sum(sizes[i]*chis[i]*ct[i] for i in range(5))/24
        if abs(mult-round(mult))<1e-6 and round(mult)==1: best=name
    return best, [round(c,3) for c in chis]
def spectrum(Dq):
    H=Hee+Dq*Hcf
    Mtot=H+1000*S2
    w,U=eigh(Mtot)
    out=[]
    i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-6: j+=1
        Q=U[:,i:j+1]
        Ssq=(w[i]/1000.0)  # approx
        # find S from S2 expectation
        s2=np.trace(Q.conj().T@S2@Q).real/Q.shape[1]
        S=(-1+np.sqrt(1+4*s2))/2
        E=np.trace(Q.conj().T@H@Q).real/Q.shape[1]
        out.append((S,E,Q))
        i=j+1
    return out
if __name__=="__main__":
    for Dq in [1.0,2.2,3.5]:
        sp=spectrum(Dq)
        E0=min(e for S,e,Q in sp)
        print("Dq/B=",Dq)
        rows=[]
        for S,E,Q in sp:
            lab,ch=label(Q,round(S*2)/2)
            rows.append((E-E0,int(round(2*S+1)),lab,Q.shape[1]//int(round(2*S+1)),ch))
        rows.sort()
        for r in rows: print("  E/B=%.4f mult=%d irrep=%s dim=%d chi=%s"%r)
