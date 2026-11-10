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
for i in range(5): f[i]/=np.sqrt(np.sum(W*f[i]**2))
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
def spec(F2,F4):
    F={0:0.0,2:F2,4:F4}
    dets=list(itertools.combinations(range(10),2))
    H=np.zeros((45,45))
    for I,(i,j) in enumerate(dets):
        for J,(k,l) in enumerate(dets):
            H[I,J]=V(i,j,k,l,F)-V(i,j,l,k,F)
    up=[I for I,(i,j) in enumerate(dets) if i%2==0 and j%2==0]
    Eup=np.sort(np.linalg.eigvalsh(H[np.ix_(up,up)]))
    z=[I for I,(i,j) in enumerate(dets) if i%2!=j%2]
    Ez=np.sort(np.linalg.eigvalsh(H[np.ix_(z,z)]))
    return Eup,Ez
for F2,F4 in [(1,0),(0,1)]:
    Eup,Ez=spec(F2,F4)
    print(F2,F4,"3F:",np.round(Eup[0],4),"3P:",np.round(Eup[7],4),"Ms0 unique:",np.unique(np.round(Ez,4)))
EOF