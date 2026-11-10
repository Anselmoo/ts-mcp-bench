import numpy as np, itertools
from scipy.special import sph_harm_y
nt, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.full(nph, 2*np.pi/nph))
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
r = {'xy':np.sqrt(15/(4*np.pi))*X*Y,'yz':np.sqrt(15/(4*np.pi))*Y*Z,'zx':np.sqrt(15/(4*np.pi))*Z*X,
     'x2y2':np.sqrt(15/(16*np.pi))*(X**2-Y**2),'z2':np.sqrt(5/(16*np.pi))*(3*Z**2-1)}
names=['xy','yz','zx','x2y2','z2']
Ak={}
for k in [0,2,4]:
    T=np.zeros((5,5,5,5),dtype=complex)
    for q in range(-k,k+1):
        Yk=sph_harm_y(k,q,TH,PH)
        Mac=np.array([[np.sum(W*r[a]*r[c]*np.conj(Yk)) for c in names] for a in names])
        Mbd=np.array([[np.sum(W*r[b]*r[d]*Yk) for d in names] for b in names])
        T+=4*np.pi/(2*k+1)*np.einsum('ac,bd->abcd',Mac,Mbd)
    print(k, np.abs(T.imag).max())
    Ak[k]=T.real
print('Ak0 [xy,xy,xy,xy]', Ak[0][0,0,0,0], 'Ak2', Ak[2][0,0,0,0])
N=10
def sord(o,s): return 2*o+s
def apply(occ, ops):
    s=list(occ); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in s: return 0,None
            p=s.index(i); sign*=(-1)**p; s.pop(p)
        else:
            if i in s: return 0,None
            p=sum(1 for x in s if x<i); sign*=(-1)**p; s.insert(p,i)
    return sign,tuple(s)
def build(nel,F,hcf):
    V=np.zeros((N,)*4)
    for k in [0,2,4]:
        for a,b,c,d in itertools.product(range(5),repeat=4):
            val=F[k]*Ak[k][a,b,c,d]
            if abs(val)<1e-14: continue
            for s1 in range(2):
                for s2 in range(2):
                    V[sord(a,s1),sord(b,s2),sord(c,s1),sord(d,s2)]+=val
    h=np.zeros((N,N))
    for a in range(5):
        for c in range(5):
            for s in range(2): h[sord(a,s),sord(c,s)]=hcf[a,c]
    states=[tuple(c) for c in itertools.combinations(range(N),nel)]
    idx={s:i for i,s in enumerate(states)}
    H=np.zeros((len(states),)*2)
    for si,s in enumerate(states):
        for i,j in itertools.product(range(N),repeat=2):
            if h[i,j]!=0:
                sg,t=apply(s,[('c',i),('a',j)])
                if t is not None: H[idx[t],si]+=sg*h[i,j]
        for a,b,c,d in itertools.product(range(N),repeat=4):
            v=V[a,b,c,d]
            if abs(v)<1e-14: continue
            sg,t=apply(s,[('c',a),('c',b),('a',d),('a',c)])
            if t is not None: H[idx[t],si]+=0.5*sg*v
    return H,states
def msub(H,states,nup):
    sel=[i for i,s in enumerate(states) if sum(1 for x in s if x%2==0)==nup and sum(1 for x in s if x%2==1)==len(s)-nup]
    return H[np.ix_(sel,sel)]
F={0:0.,2:1.0,4:0.625}
H3,st3=build(3,F,np.zeros((5,5)))
Hs=msub(H3,st3,3)
print('d3 quartet eig (F2=1,F4=.625):',np.round(np.linalg.eigvalsh(Hs),4))
import pickle; pickle.dump(Ak,open('Ak.pkl','wb'))
