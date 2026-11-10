import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
nt, nphi = 60, 120
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
TH = np.arccos(xg)[:,None]*np.ones((1,nphi)); PH = np.ones((nt,1))*phis[None,:]
W = (wg[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Y(l,m): return sph_harm_y(l,m,TH,PH)
ms=list(range(-2,3))
nvec=np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)],-1)
Rs=[(2,0,0),(-2,0,0),(0,2,0),(0,-2,0),(0,0,2),(0,0,-2)]
Vang=np.zeros(TH.shape)
for R in Rs:
    d=np.sqrt(((nvec-np.array(R))**2).sum(-1)); Vang+=1.0/d
Mlf=np.zeros((5,5),complex)
for i,m in enumerate(ms):
    for j,mp in enumerate(ms):
        Mlf[i,j]=np.sum(W*np.conj(Y(2,m))*Vang*Y(2,mp))
ev=np.linalg.eigvalsh(Mlf); t2=ev[:3].mean(); eg=ev[3:].mean()
h1=((Mlf-t2*np.eye(5))/(eg-t2)).real
def Ak(k,ma,mb,mc,md):
    tot=0
    for q in range(-k,k+1):
        Ykq=Y(k,q)
        I1=np.sum(W*np.conj(Y(2,ma))*np.conj(Ykq)*Y(2,mc))
        I2=np.sum(W*np.conj(Y(2,mb))*Ykq*Y(2,md))
        tot+=I1*I2
    return 4*np.pi/(2*k+1)*tot
A={}
for k in (2,4):
    T=np.zeros((5,5,5,5),complex)
    for a,b,c,d in itertools.product(range(5),repeat=4):
        T[a,b,c,d]=Ak(k,ms[a],ms[b],ms[c],ms[d])
    A[k]=T.real
N=10
def apply_ops(state, ops):
    st=list(state); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in st: return None,0
            p=st.index(i); sign*=(-1)**p; st.pop(p)
        else:
            if i in st: return None,0
            p=sum(1 for x in st if x<i); sign*=(-1)**p; st.insert(p,i)
    return tuple(st),sign
dets=[c for c in itertools.combinations(range(N),7) if sum(1 for x in c if x<5)-sum(1 for x in c if x>=5)==3]
idx={d:i for i,d in enumerate(dets)}
ONE=[]; TWO={2:[], 4:[]}
for j,d in enumerate(dets):
    for a in range(5):
        for b in range(5):
            for s in (0,1):
                new,sg=apply_ops(d,[('c',a+5*s),('a',b+5*s)])
                if new is not None: ONE.append((idx[new],j,sg,a,b))
    for a,b,c,dd in itertools.product(range(5),repeat=4):
        for k in (2,4):
            if abs(A[k][a,b,c,dd])<1e-12: continue
            for s1 in (0,1):
                for s2 in (0,1):
                    new,sg=apply_ops(d,[('c',a+5*s1),('c',b+5*s2),('a',dd+5*s2),('a',c+5*s1)])
                    if new is not None: TWO[k].append((idx[new],j,0.5*sg*A[k][a,b,c,dd]))
def Hmat(D10,F2,F4):
    H=np.zeros((len(dets),len(dets)))
    for i,j,sg,a,b in ONE: H[i,j]+=sg*D10*h1[a,b]
    for i,j,v in TWO[2]: H[i,j]+=F2*v
    for i,j,v in TWO[4]: H[i,j]+=F4*v
    return H
def FF(B,c=4.0):
    F4=441*c*B/35.0; F2=(441*B+5*F4)/9.0; return F2,F4
def uniq(s,tol=1e-5):
    out=[]
    for x in np.sort(s):
        if not out or abs(x-out[-1][0])>tol: out.append([x,1])
        else: out[-1][1]+=1
    return out
def trans(D10,B,c=4.0):
    F2,F4=FF(B,c)
    u=uniq(np.linalg.eigvalsh(Hmat(D10,F2,F4)))
    g=u[0][0]
    return [(x-g,m) for x,m in u[1:]]   # [(T2g,3),(A2g,1),(T1g P,3)]
# Check 4T2g, A2g, T1gP
for D,B in [(9460,900),(9460,1000)]:
    print(D,B,[(round(e,0),m) for e,m in trans(D,B)])
# fit D10 and B to bands: T2g=9460? assignment options
obs=[9460,20160,21160]
def res(p, assign):
    D10,B=p
    t=trans(D10,B)
    e={'T2g':t[0][0],'A2g':t[1][0],'T1gP':t[2][0]}
    return [e[assign[0]]-obs[0], e[assign[1]]-obs[1], e[assign[2]]-obs[2]]
import itertools as it
for assign in [('T2g','A2g','T1gP'),('T2g','T1gP','A2g')]:
    sol=least_squares(lambda p: res(p,assign), x0=[9000,900], xtol=1e-10, ftol=1e-10)
    print(assign, sol.x, np.round(sol.fun,1))
