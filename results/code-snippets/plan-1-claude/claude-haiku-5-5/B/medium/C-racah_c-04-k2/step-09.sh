
cat << 'EOF' | python3 -
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
nt, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0,2*np.pi,nph,endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
c = np.sqrt(15/(4*np.pi))
orbs = [c*X*Y, c*Y*Z, c*Z*X, c/2*(X**2-Y**2), np.sqrt(5/(16*np.pi))*(3*Z**2-1)]
orbs = [f/np.sqrt(np.sum(W*f*f)) for f in orbs]
def Gcoef(i,k,j,l):
    out={}
    for K in (0,2,4):
        s=0
        for q in range(-K,K+1):
            Ykq = sph_harm_y(K,q,TH,PH)
            A=np.sum(W*orbs[i]*orbs[k]*np.conj(Ykq)); Bv=np.sum(W*orbs[j]*orbs[l]*Ykq)
            s+=A*Bv
        out[K]=(4*np.pi/(2*K+1))*s.real
    return out
N=10
G={(i,k,j,l):Gcoef(i,k,j,l) for i,k,j,l in itertools.product(range(5),repeat=4)}
def ann(lst,x):
    if x not in lst: return None,0
    p=lst.index(x); return lst[:p]+lst[p+1:], (-1)**p
def cre(lst,x):
    if x in lst: return None,0
    p=sum(1 for y in lst if y<x); return sorted(lst+[x]), (-1)**p
def sector(states, Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9; F={0:0.0,2:F2,4:F4}
    h=np.zeros(N)
    for o in range(5):
        for s in range(2): h[2*o+s]= -4*Dq if o<3 else 6*Dq
    terms=[]
    for p,q,r,t in itertools.product(range(N),repeat=4):
        ip,sp=divmod(p,2); iq,sq=divmod(q,2); ir,sr=divmod(r,2); it,st_=divmod(t,2)
        if sp!=sr or sq!=st_: continue
        gg=G[(ip,ir,iq,it)]; val=sum(gg[K]*F[K] for K in (0,2,4))
        if abs(val)>1e-12: terms.append((p,q,r,t,0.5*val))
    idx={s:n for n,s in enumerate(states)}; M=len(states); H=np.zeros((M,M))
    for n,s in enumerate(states):
        H[n,n]+=sum(h[o] for o in s)
        for p,q,r,t,v in terms:
            l,s1=ann(list(s),r)
            if l is None: continue
            l,s2=ann(l,t)
            if l is None: continue
            l,s3=cre(l,q)
            if l is None: continue
            l,s4=cre(l,p)
            if l is None: continue
            key=tuple(l)
            if key in idx: H[idx[key],n]+=v*s1*s2*s3*s4
    return H
up=[2*o for o in range(5)]; dn=[2*o+1 for o in range(5)]
S32=[tuple(sorted(s)) for s in itertools.combinations(up,3)]
S12=[tuple(sorted(a+(b,))) for a in itertools.combinations(up,2) for b in dn]
def levels(Dq,B,C):
    e32=np.linalg.eigvalsh(sector(S32,Dq,B,C))
    e12=list(np.linalg.eigvalsh(sector(S12,Dq,B,C)))
    for qe in e32:
        j=int(np.argmin(np.abs(np.array(e12)-qe)))
        if abs(e12[j]-qe)<1e-4: e12.pop(j)
    return e32,np.array(sorted(e12))
def model(Dq,B,C):
    e32,d=levels(Dq,B,C)
    q=np.unique(np.round(e32,4)); g=q[0]
    return np.array([q[1]-g, q[2]-g, q[3]-g, d[0]-g])
obs=np.array([17430,25000,39000,15410.])
def res(p):
    Dq,B,C=p
    return (model(Dq,B,C)-obs)
sol=least_squares(res,[1743,780,3200],diff_step=1e-4)
print(sol.x, res(sol.x))
# also check 2E isn't mis-identified: print doublet levels
e32,d=levels(*sol.x); print(np.round(d[:8],1))
print("C/B", sol.x[2]/sol.x[1])
EOF