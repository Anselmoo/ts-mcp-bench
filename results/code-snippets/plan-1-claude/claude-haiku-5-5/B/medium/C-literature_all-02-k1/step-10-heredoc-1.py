import numpy as np, itertools
from scipy.special import eval_legendre
from scipy.optimize import fsolve, least_squares
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
Mk={}
for kk in [2,4]:
    F={0:0,2:0,4:0}; F[kk]=1
    Mk[kk]=np.array([[V(i,j,k,l,F)-V(i,j,l,k,F) for (k,l) in dets] for (i,j) in dets])
def levels(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    H=F2*Mk[2]+F4*Mk[4]
    eps=[-4*Dq if o<3 else 6*Dq for o in range(5)]
    for I,(i,j) in enumerate(dets): H[I,I]+=eps[i//2]+eps[j//2]
    T=np.sort(np.linalg.eigvalsh(H[np.ix_(up,up)]))
    M=np.linalg.eigvalsh(H[np.ix_(z,z)])
    S=list(M)
    for t in T:
        idx=int(np.argmin([abs(s-t) for s in S])); S.pop(idx)
    return T, np.array(sorted(S))
def classify(Dq,B,C):
    T,S=levels(Dq,B,C)
    g=T[0]
    # triplet clusters
    tc=[]
    vals=np.sort(T)
    # group in 3s and 1
    clusters=[]
    i=0
    while i<len(vals):
        j=i
        while j+1<len(vals) and abs(vals[j+1]-vals[i])<1.0: j+=1
        clusters.append((vals[i]-g,j-i+1)); i=j+1
    # singlet E pairs (count 2)
    sc=[]
    i=0
    while i<len(S):
        j=i
        while j+1<len(S) and abs(S[j+1]-S[i])<1.0: j+=1
        sc.append((S[i]-g,j-i+1)); i=j+1
    return clusters, sc
def resid(p):
    Dq,B,C=p
    T,S=levels(Dq,B,C)
    g=T[0]
    cl=[]; i=0
    vals=T
    while i<len(vals):
        j=i
        while j+1<len(vals) and abs(vals[j+1]-vals[i])<1.0: j+=1
        cl.append((vals[i]-g,j-i+1)); i=j+1
    t2=[c for c,n in cl if n==3 and c>1]
    t1P=[c for c,n in cl if n==3 and c>1]
    # 3T2 = 2nd cluster (size3), 3T1P = 3rd cluster size 3
    sz3=[c for c,n in cl if n==3]
    E_T2=sz3[1]; E_T1P=sz3[2]
    # 1E(D): lowest singlet pair (count 2) with energy > 1
    pairs=[]
    i=0
    while i<len(S):
        j=i
        while j+1<len(S) and abs(S[j+1]-S[i])<1.0: j+=1
        if j-i+1==2: pairs.append(S[i]-g)
        i=j+1
    E_1E=min(pairs)
    return np.array([E_T2-17500, E_T1P-25000, E_1E-9748])
sol=least_squares(resid,[1500,600,2500],x_scale=[1000,500,2000])
print(sol.x, resid(sol.x), sol.success)
Dq,B,C=sol.x
print("C/B",C/B)
for p in [sol.x]:
    print(classify(*p))
