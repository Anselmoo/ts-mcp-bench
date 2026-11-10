import numpy as np, itertools
from scipy.special import eval_legendre
from scipy.optimize import fsolve
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
dets=list(itertools.combinations(range(10),2))
up=[I for I,(i,j) in enumerate(dets) if i%2==0 and j%2==0]
z=[I for I,(i,j) in enumerate(dets) if i%2!=j%2]
def H_of(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    eps=[-4*Dq if o<3 else 6*Dq for o in range(5)]
    H=np.zeros((45,45))
    for I,(i,j) in enumerate(dets):
        for J,(k,l) in enumerate(dets):
            H[I,J]=V(i,j,k,l,F)-V(i,j,l,k,F)
        H[I,I]+=eps[i//2]+eps[j//2]
    return H
def levels(Dq,B,C):
    H=H_of(Dq,B,C)
    T=np.linalg.eigvalsh(H[np.ix_(up,up)])
    M=np.linalg.eigvalsh(H[np.ix_(z,z)])
    # remove triplet values from Ms=0
    S=list(M)
    for t in T:
        idx=int(np.argmin([abs(s-t) for s in S])); S.pop(idx)
    return np.sort(T), np.array(sorted(S))
if __name__=="__main__":
    for Dq in [0,500,1000,1500,2000]:
        T,S=levels(Dq,700,2800)
        print("Dq",Dq)
        print(" trip:",np.round(T-T[0],0))
        print(" sing:",np.round(S-T[0],0))
