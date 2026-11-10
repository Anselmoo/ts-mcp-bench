import numpy as np, itertools
from scipy.special import sph_harm_y
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
            A=np.sum(W*orbs[i]*orbs[k]*np.conj(Ykq))
            Bv=np.sum(W*orbs[j]*orbs[l]*Ykq)
            s+=A*Bv
        out[K]=(4*np.pi/(2*K+1))*s.real
    return out
N=10
G={}
for i,k,j,l in itertools.product(range(5),repeat=4):
    G[(i,k,j,l)]=Gcoef(i,k,j,l)
# sanity: Slater check: G0 for (ii,jj) should be 1/(4pi)*4pi... print a few
print(G[(0,0,0,0)], G[(4,4,0,0)], G[(0,0,4,4)])
np.save('/dev/null',0) if False else None
import pickle
pickle.dump(G, open('/home/G.pkl','wb')) if False else None
globals()['G']=G
states=list(itertools.combinations(range(N),3)); idx={s:n for n,s in enumerate(states)}
def ann(lst,x):
    if x not in lst: return None,0
    p=lst.index(x); return lst[:p]+lst[p+1:], (-1)**p
def cre(lst,x):
    if x in lst: return None,0
    p=sum(1 for y in lst if y<x); return sorted(lst+[x]), (-1)**p
def energy_matrix(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    F={0:0.0,2:F2,4:F4}
    h=np.zeros(N)
    for o in range(5):
        for s in range(2): h[2*o+s]= -4*Dq if o<3 else 6*Dq
    # two-electron terms: list of (p,q,r,t,val) for 1/2 g c_p+ c_q+ c_t c_r
    terms=[]
    for p,q,r,t in itertools.product(range(N),repeat=4):
        ip,sp=divmod(p,2); iq,sq=divmod(q,2); ir,sr=divmod(r,2); it,st_=divmod(t,2)
        # <p q | 1/r | r t>?? use <ab|cd>: a=p,b=q (out), c=r,d=t (in): spin a=c, b=d
        if sp!=sr or sq!=st_: continue
        gg=G[(ip,ir,iq,it)]
        val=sum(gg[K]*F[K] for K in (0,2,4))
        if abs(val)>1e-12: terms.append((p,q,r,t,0.5*val))
    M=len(states); H=np.zeros((M,M))
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
            H[idx[tuple(l)],n]+=v*s1*s2*s3*s4
    return H
H=energy_matrix(1000,600,3000)
print(np.allclose(H,H.T), np.linalg.eigvalsh(H)[:5])
