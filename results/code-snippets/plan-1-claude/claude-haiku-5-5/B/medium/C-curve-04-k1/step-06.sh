python3 - << 'EOF'
import numpy as np, itertools
import scipy.sparse as sp
from numpy.polynomial import legendre as L

B=1.0; C=3473/800.0
F2=49*B+7*C; F4=63*C/5.0
Fk={0:0.0,2:F2,4:F4}

def E(i,j):
    M=np.zeros((3,3)); M[i,j]=1; M[j,i]=1; return M/np.sqrt(2)
Bs=[E(0,1),E(1,2),E(0,2),np.diag([1,-1,0])/np.sqrt(2),np.diag([-1,-1,2])/np.sqrt(6)]
eps=np.array([-4,-4,-4,6,6],float)
for i in range(5):
    for j in range(5):
        assert abs(np.sum(Bs[i]*Bs[j])-(i==j))<1e-12

nt,npf=24,48
xg,wg=L.leggauss(nt)
th=np.arccos(xg); ph=np.arange(npf)*2*np.pi/npf
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=(np.outer(wg,np.ones(npf))*(2*np.pi/npf)).reshape(-1)
U=np.stack([np.sin(TH)*np.cos(PH),np.sin(TH)*np.sin(PH),np.cos(TH)],-1).reshape(-1,3)
f=np.array([np.einsum('pi,ij,pj->p',U,b,U) for b in Bs])
nrm=np.sqrt(np.einsum('ip,p,ip->i',f,W,f)); f=f/nrm[:,None]
G=np.einsum('ip,p,jp->ij',f,W,f); assert np.allclose(G,np.eye(5),atol=1e-10)
cosg=U@U.T
pairs=[(a,c) for a in range(5) for c in range(5)]
g=np.array([f[a]*f[c] for a,c in pairs])*W[None,:]
Vk={k:g@L.legval(cosg,[0]*k+[1])@g.T for k in (0,2,4)}
V=np.zeros((5,5,5,5))
for k in (0,2,4):
    M=Vk[k]*Fk[k]
    for ia,(a,c) in enumerate(pairs):
        for ib,(b,d) in enumerate(pairs):
            V[a,b,c,d]+=M[ia,ib]

NS=20
states=sorted(sum(1<<i for i in c) for c in itertools.combinations(range(NS),5))
idx={s:n for n,s in enumerate(states)}
D=len(states)
def cdag_c(i,j,m):
    if not (m>>j)&1: return None,0
    s=(-1)**bin(m&((1<<j)-1)).count('1')
    m1=m^(1<<j)
    if (m1>>i)&1: return None,0
    s*=(-1)**bin(m1&((1<<i)-1)).count('1')
    return m1|(1<<i), s
def onebody(i,j):
    rows=[];cols=[];vals=[]
    for n,m in enumerate(states):
        mm,s=cdag_c(i,j,m)
        if mm is None: continue
        rows.append(idx[mm]); cols.append(n); vals.append(s)
    return sp.csr_matrix((vals,(rows,cols)),shape=(D,D))
Eorb={(a,c):(onebody(2*a,2*c)+onebody(2*a+1,2*c+1)).tocsr() for a in range(5) for c in range(5)}
Hee=sp.csr_matrix((D,D))
for a,b,c,d in itertools.product(range(5),repeat=4):
    v=V[a,b,c,d]
    if abs(v)>1e-14:
        Hee=Hee+0.5*v*(Eorb[(a,c)]@Eorb[(b,d)])
        if b==c: Hee=Hee-0.5*v*Eorb[(a,d)]
Hee=Hee.tocsr()
Sp=sum(onebody(2*p,2*p+1) for p in range(10)).tocsr()
Sm=Sp.T.tocsr()
Nup=np.array([sum((m>>(2*p))&1 for p in range(10)) for m in states])
Ndn=np.array([sum((m>>(2*p+1))&1 for p in range(10)) for m in states])
Sz=(Nup-Ndn)/2.0
S2=(Sm@Sp)+sp.diags(Sz**2+Sz)
blk=np.where(Nup==3)[0]
Hb=Hee[blk][:,blk].toarray()
S2b=S2[blk][:,blk].toarray()
print("block dim",len(blk),"herm err",np.abs(Hb-Hb.T).max())

def rot(axis,ang):
    axis=np.array(axis,float); axis/=np.linalg.norm(axis)
    K=np.array([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
    return np.eye(3)+np.sin(ang)*K+(1-np.cos(ang))*K@K
blkpos={n:k for k,n in enumerate(blk)}
def manybody(R):
    Dm=np.array([[np.sum(Bs[bb]*(R@Bs[a]@R.T)) for a in range(5)] for bb in range(5)])
    rows=[];cols=[];vals=[]
    for n in blk:
        m=states[n]
        occ=[i for i in range(NS) if (m>>i)&1]
        ket={0:1.0}
        for i in reversed(occ):
            a=i//2; sg=i%2
            new={}
            for mm,cf in ket.items():
                for b in range(5):
                    if abs(Dm[b,a])<1e-14: continue
                    j=2*b+sg
                    if (mm>>j)&1: continue
                    s=(-1)**bin(mm&((1<<j)-1)).count('1')
                    m2=mm|(1<<j)
                    new[m2]=new.get(m2,0)+cf*Dm[b,a]*s
            ket=new
        for mm,cf in ket.items():
            if abs(cf)>1e-14:
                rows.append(blkpos[idx[mm]]); cols.append(blkpos[n]); vals.append(cf)
    return sp.csr_matrix((vals,(rows,cols)),shape=(len(blk),len(blk))).toarray()
classes={'E':np.eye(3),'C3':rot([1,1,1],2*np.pi/3),'C2':rot([0,0,1],np.pi),'C4':rot([0,0,1],np.pi/2),"C2'":rot([1,1,0],np.pi)}
Umats={k:manybody(R) for k,R in classes.items()}
irr={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
ordc=['E','C3','C2','C4',"C2'"]
sz=np.array([1,8,3,6,6])
def label(chi):
    return [k for k,v in irr.items() if abs(np.sum(sz*np.array(v)*chi)/24-1)<1e-6]
# check U is a representation-compatible: commutes with Hb at Dq=1
Hlf=sum(eps[a]*Eorb[(a,a)] for a in range(5))
Hfull=(Hee+1.45*Hlf).tocsr()[blk][:,blk].toarray()
print("commutator check", max(np.abs(Umats[k]@Hfull-Hfull@Umats[k]).max() for k in classes))

def analyze(Dq):
    Hf=(Hee+Dq*Hlf).tocsr()[blk][:,blk].toarray()
    w,v=np.linalg.eigh(Hf)
    clusters=[]; i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-7: j+=1
        clusters.append((i,j)); i=j+1
    res=[]
    for (i,j) in clusters:
        vv=v[:,i:j+1]
        S2v=np.trace(vv.T@S2b@vv)/(j-i+1)
        S=(-1+np.sqrt(1+4*S2v))/2
        chi=np.real(np.array([np.trace(vv.T@Umats[k]@vv) for k in ordc]))
        res.append(dict(E=w[i],dim=j-i+1,mult=int(round(2*S+1)),irr=label(chi),chi=chi))
    return res
for Dq in [1.45,2.55,3.25]:
    res=analyze(Dq)
    g=res[0]
    print("Dq/B=",Dq,"clusters",len(res),"ground:",g['mult'],g['irr'],round(g['E'],5))
    for r in res[:12]:
        print(f"  E/B={r['E']-g['E']:.4f} dim={r['dim']} mult={r['mult']} irr={r['irr']} chi={np.round(r['chi'],2)}")
EOF