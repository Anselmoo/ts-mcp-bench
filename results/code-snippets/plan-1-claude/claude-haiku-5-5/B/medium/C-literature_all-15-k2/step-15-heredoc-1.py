import numpy as np, itertools
from scipy.special import sph_harm_y
nt, nphi = 30, 60
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
raw=[X*Yc, Yc*Z, X*Z, X**2-Yc**2, 3*Z**2-1]
vals=np.array([v/np.sqrt(np.sum(W*v*v)) for v in raw])
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Yk=np.conj(sph_harm_y(k,q,TH,PH))
        s+= np.sum(W*a*c*Yk)*np.conj(np.sum(W*b*d*Yk))
    return 4*np.pi/(2*k+1)*s
A={k:np.zeros((5,5,5,5)) for k in (2,4)}
for k in (2,4):
    for a,b,c,d in itertools.product(range(5),repeat=4):
        A[k][a,b,c,d]=np.real(ang(k,vals[a],vals[b],vals[c],vals[d]))
N=10
def nup(s): return sum(1 for o in range(5) if s>>(2*o)&1)
def ndn(s): return sum(1 for o in range(5) if s>>(2*o+1)&1)
states=[sum(1<<i for i in c) for c in itertools.combinations(range(N),7)]
def ann(s,i):
    if not (s>>i)&1: return None,0
    return s^(1<<i), (-1)**bin(s&((1<<i)-1)).count('1')
def cre(s,i):
    if (s>>i)&1: return None,0
    return s|(1<<i), (-1)**bin(s&((1<<i)-1)).count('1')
def build(sts):
    idx={s:i for i,s in enumerate(sts)}; n=len(sts)
    Hk={k:np.zeros((n,n)) for k in (2,4)}
    for s in sts:
        col=idx[s]
        for i,j,kk,l in itertools.product(range(N),repeat=4):
            if i==j or kk==l or i%2!=kk%2 or j%2!=l%2: continue
            s1,g1=ann(s,kk)
            if s1 is None: continue
            s2,g2=ann(s1,l)
            if s2 is None: continue
            s3,g3=cre(s2,j)
            if s3 is None: continue
            s4,g4=cre(s3,i)
            if s4 is None: continue
            if s4 in idx:
                for k in (2,4): Hk[k][idx[s4],col]+=0.5*A[k][i//2,j//2,kk//2,l//2]*g1*g2*g3*g4
    Num=np.zeros((5,n,n))
    for s in sts:
        c=idx[s]
        for o in range(5): Num[o,c,c]=((s>>(2*o))&1)+((s>>(2*o+1))&1)
    return Hk,Num
S32=build([s for s in states if nup(s)-ndn(s)==3])
S12=build([s for s in states if nup(s)-ndn(s)==1])
def H(sec,Dq,B,C):
    Hk,Num=sec
    F4=C*441/35; F2=(441*B+5*F4)/9
    h=[-4*Dq,-4*Dq,-4*Dq,6*Dq,6*Dq]
    M=F2*Hk[2]+F4*Hk[4]
    for o in range(5): M=M+h[o]*Num[o]
    return M
def distinct(e,tol=0.5):
    out=[]
    for v in np.sort(e):
        if out and abs(v-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([v,1])
    return out
def doublets(Dq,B,C):
    q=np.linalg.eigvalsh(H(S32,Dq,B,C)); m=list(np.sort(np.linalg.eigvalsh(H(S12,Dq,B,C))))
    for e in q: m.pop(int(np.argmin([abs(x-e) for x in m])))
    return distinct(np.array(m))
for C in [3500,4000,4500,5000]:
    d=doublets(890,915,C); g=np.linalg.eigvalsh(H(S32,890,915,C)).min()
    print(C,[(round(v-g),m) for v,m in d if m==3][:6])
