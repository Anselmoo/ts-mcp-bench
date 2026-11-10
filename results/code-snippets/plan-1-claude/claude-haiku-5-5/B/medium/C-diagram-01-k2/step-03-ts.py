import numpy as np, itertools
B=828.0; C=3390.0
F4=441*C/35.0; F2=(441*B+5*F4)/9.0          # Racah: B=(9F2-5F4)/441, C=35F4/441
Fk={2:F2,4:F4}

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
G=np.clip(P@P.T,-1,1)
Pl={2:(3*G**2-1)/2, 4:(35*G**4-30*G**2+3)/8}
X=np.einsum('ia,ib->iab',Phi,Phi).reshape(len(W),25)
Xw=X*W[:,None]
A={k:Xw.T@Pl[k]@Xw for k in Pl}   # indexed [(a c),(b d)]
print("orthonormal check:", np.allclose((Phi*W[:,None]).T@Phi,np.eye(5)))

NSO=10
V=np.zeros((NSO,)*4)
for a,b,c,d in itertools.product(range(5),repeat=4):
    for sa,sb in itertools.product(range(2),repeat=2):
        for sc,sd in [(sa,sb)]:
            pass
for a,b,c,d in itertools.product(range(5),repeat=4):
    for sa,sb in itertools.product(range(2),repeat=2):
        val=sum(Fk[k]*A[k][a*5+c,b*5+d] for k in Pl)
        V[2*a+sa,2*b+sb,2*c+sa,2*d+sb]=val   # spin: s_a=s_c, s_b=s_d

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
        if abs(v)<1e-14: continue
        s1,st1=annih(c,st)
        if s1==0: continue
        s2,st2=annih(d,st1)
        if s2==0: continue
        s3,st3=create(b,st2)
        if s3==0: continue
        s4,st4=create(a,st3)
        if s4==0: continue
        Hee[index[st4],col]+=0.5*v*s1*s2*s3*s4

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
S2=Sm@Sp+np.diag(Sz*Sz)+np.diag(Sz)
print("S2 eigen:",np.unique(np.round(np.linalg.eigvalsh(S2),6)))
print("Hee eig at Dq=0 (x B):",np.unique(np.round(np.linalg.eigvalsh(Hee)/B,4)))

occ_orb=[[i//2 for i in st] for st in basis]
def hdiag(dq):
    return np.diag([sum((-4*dq if o in (0,1,2) else 6*dq) for o in oo) for oo in occ_orb])
# note orbital index: 0 xy,1 yz,2 zx (t2g); 3 x2-y2, 4 z2 (eg)

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
    return 2 if all(abs(M[i,i])>0.5 for i in range(3)) else 4
classes=[[M for M in grp if cls(M)==k] for k in range(5)]
sizes=[len(c) for c in classes]; assert sizes==[1,8,3,6,6], sizes

def Dmat(g):
    Pg=P@np.linalg.inv(g).T
    return (Phi*W[:,None]).T@(raw(Pg)*Nrm)
def manybody(g):
    U=np.kron(Dmat(g),np.eye(2))
    M=np.zeros((D,D))
    for col,S in enumerate(basis):
        for row,T in enumerate(basis):
            M[row,col]=np.linalg.det(U[np.ix_(T,S)])
    return M
Mclass=[[manybody(g) for g in classes[k]] for k in range(5)]
print("rep check (orthogonal):", np.allclose(Mclass[1][0]@Mclass[1][0].T, np.eye(D)))

irreps={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
sup={1:'¹',2:'²',3:'³',4:'⁴',5:'⁵',6:'⁶'}
sub={'A1':'A₁','A2':'A₂','E':'E','T1':'T₁','T2':'T₂'}

def analyze(dq):
    H=Hee+hdiag(dq)
    w,vecs=np.linalg.eigh(H+1e5*S2)
    terms=[]; i=0
    while i<D:
        j=i
        while j+1<D and abs(w[j+1]-w[i])<1e-4: j+=1
        Vc=vecs[:,i:j+1]; m=j-i+1
        E=np.trace(Vc.T@H@Vc)/m
        s2=np.trace(Vc.T@S2@Vc)/m
        mult=int(round(np.sqrt(1+4*s2)))
        chis=[sum(np.trace(Vc.T@M@Vc) for M in Mclass[k])/sizes[k] for k in range(5)]
        for nm,ch in irreps.items():
            n=int(round((sum(sizes[k]*chis[k]*ch[k] for k in range(5))/24).real))
            for _ in range(n):
                terms.append((mult,nm,E,m))
        i=j+1
    return terms

if __name__=='__main__':
    import pickle
    res={}
    for x in np.arange(0,4.01,0.5):
        terms=analyze(x*B)
        terms.sort(key=lambda t:t[2])
        E0=terms[0][2]
        print(f"Dq/B={x:.1f}: levels={len(terms)}")
        for m,n,e,deg in terms[:8]:
            print(f"   {sup[m]}{sub[n]}g  E/B={(e-E0)/B:10.5f}  (cluster size {deg})")
        res[round(float(x),1)]=[(f"{sup[m]}{sub[n]}g",(e-E0)/B) for m,n,e,_ in terms]
    pickle.dump(res,open('res.pkl','wb'))
