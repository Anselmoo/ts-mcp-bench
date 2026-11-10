cat << 'EOF' > /tmp/ts.py
import numpy as np, scipy.linalg as sla, hashlib, os
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

B=1.0; Cr=3390/828
F2=49*B+7*Cr*B; F4=12.6*Cr*B  # Racah: B=(9F2-5F4)/441, C=35F4/441

# angular grid on sphere
x,wx=leggauss(12); pts=[]; wts=[]
for xi,wi in zip(x,wx):
    s=np.sqrt(1-xi**2)
    for p in np.arange(24)*2*np.pi/24:
        pts.append([s*np.cos(p),s*np.sin(p),xi]); wts.append(wi*2*np.pi/24)
P=np.array(pts); W=np.array(wts)
def dfun(Q):
    X,Y,Z=Q.T
    return np.array([3*Z**2-1, X**2-Y**2, X*Y, Y*Z, Z*X])  # order: z2,x2-y2,xy,yz,zx
f=dfun(P); f=f/np.sqrt((f*f*W).sum(1))[:,None]
assert np.allclose((f*W)@f.T, np.eye(5), atol=1e-10)

# angular integrals A_k
cosg=np.clip(P@P.T,-1,1)
Fk={0:0.0,2:F2,4:F4}
Vorb=np.zeros((5,5,5,5))
for k,Fv in Fk.items():
    Pk=eval_legendre(k,cosg)
    G=f[:,None,:]*f[None,:,:]          # (a,c,N)
    A=np.einsum('acI,IJ,bdJ->acbd',G*W[None,None,:],Pk,G)
    # V_{ab,cd}=sum_k F_k A[a,c,b,d]
    Vorb+=Fv*np.einsum('acbd->abcd',A)

# spin-orbital index: 2*o+s
nso=10
V=np.zeros((nso,)*4)
for a in range(5):
  for b in range(5):
    for c in range(5):
      for d in range(5):
        for sa in range(2):
          for sb in range(2):
            for sc in range(2):
              for sd in range(2):
                if sa==sc and sb==sd:
                    V[2*a+sa,2*b+sb,2*c+sc,2*d+sd]=Vorb[a,b,c,d]

# Fock space (JW)
D=1<<nso
def ops(j):
    cd=np.zeros((D,D)); 
    for n in range(D):
        if not (n>>j)&1:
            sign=(-1)**bin(n&((1<<j)-1)).count('1')
            cd[n|(1<<j),n]=sign
    return cd, cd.T.copy()
cdag=[];cann=[]
for j in range(nso):
    a,b=ops(j); cdag.append(a); cann.append(b)

# two-body
Hee=np.zeros((D,D))
for p,q,r,s in zip(*np.nonzero(np.abs(V)>1e-14)):
    Hee+=0.5*V[p,q,r,s]*cdag[p]@cdag[q]@cann[s]@cann[r]
# one-body crystal field (per Dq): eg +6, t2g -4
cfw=np.array([6,6,-4,-4,-4])
Hcf=np.zeros((D,D))
for o in range(5):
    for s in range(2):
        j=2*o+s; Hcf+=cfw[o]*cdag[j]@cann[j]

idx=[n for n in range(D) if bin(n).count('1')==3]
Sz=np.array([0.5*(sum(((n>>(2*o))&1)-((n>>(2*o+1))&1) for o in range(5))) for n in idx])
Sp=np.zeros((D,D))
for o in range(5): Sp+=cdag[2*o]@cann[2*o+1]
Sp3=Sp[np.ix_(idx,idx)]; Sm3=Sp3.T
S2=Sm3@Sp3+np.diag(Sz*(Sz+1))
J=[i for i in range(len(idx)) if abs(Sz[i]-0.5)<1e-9]
Hee3=Hee[np.ix_(idx,idx)][np.ix_(J,J)]
Hcf3=Hcf[np.ix_(idx,idx)][np.ix_(J,J)]
S2J=S2[np.ix_(J,J)]
w,U=np.linalg.eigh(S2J)
Q4=U[:,np.abs(w-3.75)<1e-8]; Q2=U[:,np.abs(w-0.75)<1e-8]
print("dims quartet/doublet:",Q4.shape[1],Q2.shape[1])

# group reps
def rot(axis,ang):
    a=np.array(axis,float); a/=np.linalg.norm(a)
    K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
    return np.eye(3)+np.sin(ang)*K+(1-np.cos(ang))*K@K
classes={'E':(np.eye(3),1),'C3':(rot([1,1,1],2*np.pi/3),8),'C2':(rot([0,0,1],np.pi),3),
         'C4':(rot([0,0,1],np.pi/2),6),"C2'":(rot([1,1,0],np.pi),6)}
irr_chars={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
ckeys=['E','C3','C2','C4',"C2'"]
def Dmat(R):
    Pr=(R.T@P.T).T
    fr=dfun(Pr); fr=fr/np.sqrt((fr*fr*W).sum(1))[:,None]
    return (fr*W)@f.T
def Gam_full(R):
    Dm=Dmat(R)
    u=np.kron(Dm,np.eye(2))
    K=sla.logm(u)
    Og=np.zeros((D,D),complex)
    for p in range(nso):
        for q in range(nso):
            if abs(K[p,q])>1e-14: Og+=K[p,q]*cdag[p]@cann[q]
    G=sla.expm(Og)
    return G[np.ix_(idx,idx)][np.ix_(J,J)]
Gs={k:Gam_full(classes[k][0]) for k in ckeys}
# check Gamma commutes with Hee
for k in ckeys: assert np.allclose(Gs[k]@Hee3-Hee3@Gs[k],0,atol=1e-8)

def levels(Dq):
    out=[]
    for S,Q,lab in [(2,Q4,'4'),(1,Q2,'2')]:
        Hb=Q.T@(Hee3+Dq*Hcf3)@Q
        E,Wv=np.linalg.eigh(Hb)
        i=0
        while i<len(E):
            j=i
            while j+1<len(E) and abs(E[j+1]-E[i])<1e-7: j+=1
            Wc=Wv[:,i:j+1]; m=Wc.shape[1]
            chi=[]
            for k in ckeys:
                Gb=Q.T@Gs[k]@Q
                chi.append(np.trace(Wc.conj().T@Gb@Wc).real)
            csz=[classes[k][1] for k in ckeys]
            for name,ch in irr_chars.items():
                n=sum(csz[c]*chi[c]*ch[c] for c in range(5))/24
                n=int(round(n))
                for _ in range(n):
                    out.append((E[i],lab+name+'g'))
            i=j+1
    out.sort(key=lambda t:t[0])
    E0=out[0][0]
    return [(e-E0,l) for e,l in out]

grid=np.arange(0,4.01,0.5)
rows=[]
for Dq in grid:
    L=levels(Dq)[:6]
    rows.append((Dq,L))
    print(f"Dq/B={Dq:.1f}: "+", ".join(f"{l} {e:.4f}" for e,l in L))

# fine grid for plot
fg=np.linspace(0,4,81)
allL={Dq:levels(Dq) for Dq in fg}
plt.figure(figsize=(7,9))
from collections import defaultdict
tracks=defaultdict(list)
for Dq in fg:
    cnt=defaultdict(int)
    for e,l in allL[Dq]:
        tracks[(l,cnt[l])].append((Dq,e)); cnt[l]+=1
for key,pts_ in tracks.items():
    if len(pts_)==len(fg):
        xs,ys=zip(*pts_)
        if ys[0]<=35:
            plt.plot(xs,ys,'b-' if key[0][0]=='4' else 'r--',lw=1)
            if key[1]==0 and ys[-1]<=45: plt.text(xs[-1],ys[-1],key[0],fontsize=7)
plt.xlabel('Dq/B'); plt.ylabel('E/B'); plt.title('Tanabe-Sugano diagram d3 octahedral (C/B=%.3f)'%Cr)
plt.xlim(0,4.4); plt.ylim(0,45)
plt.savefig('diagram.png',dpi=120)
h=hashlib.sha256(open('diagram.png','rb').read()).hexdigest()
print(os.path.abspath('diagram.png'),h)
EOF
cd /tmp && python3 ts.py