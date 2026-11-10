cat << 'EOF' > /tmp/ts.py
import numpy as np, itertools, hashlib, os
B=828.0; C=3390.0
F4=441*C/35.0; F2=(441*B+5*F4)/9.0          # Racah: B=(9F2-5F4)/441, C=35F4/441
Fk={2:F2,4:F4}

# quadrature on sphere
xg,wg=np.polynomial.legendre.leggauss(30)
phis=np.linspace(0,2*np.pi,60,endpoint=False)
pts=[];ws=[]
for x,w in zip(xg,wg):
    s=np.sqrt(1-x*x)
    for p in phis:
        pts.append([s*np.cos(p),s*np.sin(p),x]); ws.append(w*2*np.pi/60)
P=np.array(pts); W=np.array(ws)

def raw(n):
    x,y,z=n[:,0],n[:,1],n[:,2]
    return np.stack([x*y,y*z,z*x,x*x-y*y,2*z*z-x*x-y*y],axis=1)
R0=raw(P)
Nrm=1/np.sqrt((W[:,None]*R0**2).sum(0))
Phi=R0*Nrm
G=np.einsum('ik,jk->ij',P,P).clip(-1,1)
Pl={2:(3*G**2-1)/2, 4:(35*G**4-30*G**2+3)/8}
X=np.einsum('ia,ib->iab',Phi,Phi).reshape(len(W),25)
Xw=X*W[:,None]
A={k:Xw.T@Pl[k]@Xw for k in Pl}   # [(a c),(b d)]

# spin-orbitals: idx=orb*2+spin
NSO=10
V=np.zeros((NSO,)*4)
for a,b,c,d in itertools.product(range(5),repeat=4):
    for sa in range(2):
        for sb in range(2):
            for sc in range(2):
                for sd in range(2):
                    if sa!=sc or sb!=sd: continue
                    val=sum(Fk[k]*A[k][a*5+c,b*5+d] for k in Pl)
                    V[2*a+sa,2*b+sb,2*c+sc,2*d+sd]=val

# basis: 3-electron determinants
basis=list(itertools.combinations(range(NSO),3))
index={s:i for i,s in enumerate(basis)}
D=len(basis)

def create(i,st):
    if i in st: return 0,None
    sign=(-1)**sum(1 for x in st if x<i)
    return sign, tuple(sorted(st+(i,)))
def annih(i,st):
    if i not in st: return 0,None
    sign=(-1)**sum(1 for x in st if x<i)
    return sign, tuple(x for x in st if x!=i)

Hee=np.zeros((D,D))
for col,st in enumerate(basis):
    for c,d,b,a in itertools.product(range(NSO),repeat=4):
        v=V[a,b,c,d]
        if v==0: continue
        s1,st1=annih(c,st)
        if s1==0: continue
        s2,st2=annih(d,st1)
        if s2==0: continue
        s3,st3=create(b,st2)
        if s3==0: continue
        s4,st4=create(a,st3)
        if s4==0: continue
        Hee[index[st4],col]+=0.5*v*s1*s2*s3*s4

# S^2
Sz=np.zeros(D); Sp=np.zeros((D,D))
for col,st in enumerate(basis):
    Sz[col]=sum(0.5 if i%2==0 else -0.5 for i in st)
    for o in range(5):
        s1,st1=annih(2*o+1,st)
        if s1==0: continue
        s2,st2=create(2*o,st1)
        if s2==0: continue
        Sp[index[st2],col]+=s1*s2
Sm=Sp.T
S2=Sm@Sp+np.diag(Sz*Sz)+np.diag(Sz)  # S-S+ + Sz^2 + Sz? (S^2 = S-S+ + Sz^2 + Sz)
# Sm@Sp = S- S+ ; check eigen
# orbital energies
def hdiag(dq):
    e=np.zeros(D)
    for col,st in enumerate(basis):
        e[col]=sum((-4*dq if (i//2) in (0,1,2) else 6*dq) for i in st)
    return np.diag(e)

# O group: signed permutations with det +1
grp=[]
for perm in itertools.permutations(range(3)):
    for sg in itertools.product([1,-1],repeat=3):
        M=np.zeros((3,3))
        for r,(c,s) in enumerate(zip(perm,sg)): M[r,c]=s
        if round(np.linalg.det(M))==1: grp.append(M)
assert len(grp)==24
def cls(M):
    t=round(np.trace(M))
    if t==3: return 0
    if t==0: return 1
    if t==1: return 3
    if t==-1:
        return 2 if all(abs(M[i,i])>0.5 for i in range(3)) else 4
classes=[[M for M in grp if cls(M)==k] for k in range(5)]
sizes=[len(c) for c in classes]; assert sizes==[1,8,3,6,6]
def Dmat(g):
    Pg=P@np.linalg.inv(g).T   # points g^{-1} n
    return Phi.T@(W[:,None]*raw(Pg)*Nrm).__array__() if False else (Phi*W[:,None]).T@(raw(Pg)*Nrm)
def manybody(g):
    Dm=Dmat(g); U=np.kron(Dm,np.eye(2))
    M=np.zeros((D,D))
    for col,S in enumerate(basis):
        for row,T in enumerate(basis):
            M[row,col]=np.linalg.det(U[np.ix_(T,S)])
    return M
Mg=[manybody(classes[k][0]) for k in range(5)]
# average class characters later per element
chars_ir={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
Mclass=[]
for k in range(5):
    Mclass.append([manybody(g) for g in classes[k]])

def analyze(dq):
    H=Hee+hdiag(dq)
    Lam=1e5
    w,vecs=np.linalg.eigh(H+Lam*S2)
    terms=[]
    i=0
    while i<D:
        j=i
        while j+1<D and abs(w[j+1]-w[i])<1e-4: j+=1
        Vc=vecs[:,i:j+1]; m=j-i+1
        E=np.trace(Vc.T@H@Vc)/m
        s2=np.trace(Vc.T@S2@Vc)/m
        chis=[np.trace(Vc.T@np.mean([M for M in Mclass[k]],axis=0)@Vc) for k in range(5)]
        # class-average of traces over class members
        chis=[sum(np.trace(Vc.T@M@Vc) for M in Mclass[k])/sizes[k] for k in range(5)]
        mult=int(round(np.sqrt(1+4*s2)))
        for name,ch in chains if False else []: pass
        for name,ch in chi_items:
            n=sum(sizes[k]*chis[k]*ch[k] for k in range(5))/24
            n=int(round(n.real))
            for _ in range(n):
                terms.append((mult,name,E))
        i=j+1
    return terms
chi_items=[(nm+'g',ch) for nm,ch in chars_ir.items()]
chi_items=[('A1g',chars_ir['A1']),('A2g',chars_ir['A2']),('Eg',chars_ir['E']),('T1g',chars_ir['T1']),('T2g',chars_ir['T2'])]
sup={'1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶'}
sub=str.maketrans('AET','AET')
def lab(mult,name):
    nm=name[:-1]; g='g'
    nm=nm.replace('1','₁').replace('2','₂')
    return sup[str(mult)]+nm[0]+nm[1:]+ 'g' if False else sup[str(mult)]+name[:-1].replace('A1','A₁').replace('A2','A₂').replace('T1','T₁').replace('T2','T₂')+'g'

if __name__=='__main__':
    # check: 4P-4F gap should be 15B at dq=0
    res={}
    for x in np.arange(0,4.01,0.5):
        dq=x*B
        terms=analyze(dq)
        terms.sort(key=lambda t:t[2])
        E0=terms[0][2]
        res[round(x,1)]=[(lab(m,n),(e-E0)/B) for m,n,e in terms]
        print(f"Dq/B={x:.1f}: total terms={len(terms)}")
        for m,n,e in terms[:8]:
            print(f"   {lab(m,n):8s} {(e-E0)/B:10.4f}")
    import pickle; pickle.dump(res,open('/tmp/res.pkl','wb'))
EOF
cd /tmp && python3 ts.py