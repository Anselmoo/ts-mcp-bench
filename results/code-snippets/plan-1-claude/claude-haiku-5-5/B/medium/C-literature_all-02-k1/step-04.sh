cd ~ 2>/dev/null; python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import eval_legendre
nt, nph = 24, 48
x, wt = np.polynomial.legendre.leggauss(nt)
pts=[]; W=[]
for ct,w in zip(x,wt):
    st=np.sqrt(1-ct*ct)
    for k in range(nph):
        ph=2*np.pi*k/nph
        pts.append([st*np.cos(ph), st*np.sin(ph), ct]); W.append(w*2*np.pi/nph)
P=np.array(pts); W=np.array(W)
X,Y,Z=P.T
f=np.array([X*Y, Y*Z, X*Z, (3*Z*Z-1), X*X-Y*Y])
for i in range(5):
    f[i]/=np.sqrt(np.sum(W*f[i]**2))
G=np.array([[np.sum(W*f[i]*f[j]) for j in range(5)] for i in range(5)])
assert np.allclose(G,np.eye(5),atol=1e-10), G
cosg=P@P.T
Tk={}
for k in [0,2,4]:
    Pk=eval_legendre(k,cosg)
    T=np.zeros((5,5,5,5))
    for a in range(5):
        for c in range(5):
            g=W*f[a]*f[c]
            for b in range(5):
                for d in range(5):
                    T[a,c,b,d]=g@Pk@(W*f[b]*f[d])
    Tk[k]=T
def V(p,q,r,s,F):
    op,sp=divmod(p,2); oq,sq=divmod(q,2); orr,sr=divmod(r,2); os_,ss=divmod(s,2)
    if sp!=sr or sq!=ss: return 0.0
    return sum(F[k]*Tk[k][op,orr,oq,os_] for k in [0,2,4])
def energies(Dq,B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    eps=np.array([-4*Dq if o in (0,1,2) else 6*Dq for o in range(5)])
    dets=list(itertools.combinations(range(10),2))
    n=len(dets)
    H=np.zeros((n,n))
    for I,(i,j) in enumerate(dets):
        for J,(k,l) in enumerate(dets):
            val=V(i,j,k,l,F)-V(i,j,l,k,F)
            if I==J: val+= eps[i//2]+eps[j//2]
            H[I,J]=val
    up=[I for I,(i,j) in enumerate(dets) if i%2==0 and j%2==0]
    Eup=np.sort(np.linalg.eigvalsh(H[np.ix_(up,up)]))
    z=[I for I,(i,j) in enumerate(dets) if i%2!=j%2]
    Ez=np.sort(np.linalg.eigvalsh(H[np.ix_(z,z)]))
    return Eup, Ez
# free-ion check: B=1000, C=4000 ; expect 3P-3F gap = 15B (Racah, with C 3P-3F = 15B+... ) 
Eup,Ez=energies(0,1000,4000)
print("triplet Ms=1 levels:", np.round(Eup-Eup[0],1))
print("Ms=0 levels:", np.round(Ez-Eup[0],1))
EOF