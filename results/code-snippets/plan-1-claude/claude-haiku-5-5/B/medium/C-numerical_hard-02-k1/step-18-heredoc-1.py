import numpy as np
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),ph,indexing='ij')
W=(wg[:,None]*np.ones(nphi)[None,:])*(2*np.pi/nphi)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
orbs={'xy':x*y,'yz':y*z,'zx':z*x,'x2y2':x*x-y*y,'z2':3*z*z-1}
names=list(orbs)
for n in names: orbs[n]=orbs[n]/np.sqrt(np.sum(W*orbs[n]**2))
def realY(l,m,TH,PH):
    if m==0: return sph_harm_y(l,0,TH,PH).real
    if m>0: return np.sqrt(2)*(-1)**m*sph_harm_y(l,m,TH,PH).real
    return np.sqrt(2)*(-1)**m*sph_harm_y(l,-m,TH,PH).imag
def Vang(k):
    Yk=[realY(k,q,TH,PH) for q in range(-k,k+1)]
    M=np.zeros((5,5,len(Yk)))
    for i,a in enumerate(names):
        for j,c in enumerate(names):
            for q,Y in enumerate(Yk): M[i,j,q]=np.sum(W*orbs[a]*orbs[c]*Y)
    return np.einsum('acq,bdq->acbd',M,M)*4*np.pi/(2*k+1)
A2=Vang(2);A4=Vang(4)
N=10
states=[s for s in range(1<<N) if bin(s).count('1')==4]
idx={s:i for i,s in enumerate(states)}; D=len(states)
def cop(s,ops):
    sign=1; t=s
    for op,i in ops:
        if op=='c':
            if not (t>>i)&1: return None
            sign*=(-1)**bin(t&((1<<i)-1)).count('1'); t&=~(1<<i)
        else:
            if (t>>i)&1: return None
            sign*=(-1)**bin(t&((1<<i)-1)).count('1'); t|=(1<<i)
    return sign,t
terms=[(a,b,c,d) for a in range(N) for b in range(N) for c in range(N) for d in range(N) if a%2==c%2 and b%2==d%2]
tb=[]
for s in states:
    for (a,b,c,d) in terms:
        r=cop(s,[('c',c),('c',d),('d',b),('d',a)])
        if r: tb.append((idx[r[1]],idx[s],a,b,c,d,r[0]))
Sp=np.zeros((D,D))
for s in states:
    for o in range(5):
        r=cop(s,[('c',2*o),('d',2*o+1)])
        if r: Sp[idx[r[1]],idx[s]]+=r[0]
Sz=np.array([0.5*sum(((s>>(2*o))&1)-((s>>(2*o+1))&1) for o in range(5)) for s in states])
S2=np.diag(Sz**2)+0.5*(Sp@Sp.T+Sp.T@Sp)
onebody=[]
for s in states:
    for p in range(N):
        r=cop(s,[('c',p),('d',p)])
        if r: onebody.append((idx[r[1]],idx[s],p//2,r[0]))
sl=np.where(np.abs(Sz-1)<1e-9)[0]; SS=S2[np.ix_(sl,sl)]
def levels(Dq,B):
    C=4.3*B
    F4=C*441/35.0; F2=(B*441+5*F4)/9.0
    Vee=F2*A2+F4*A4
    H=np.zeros((D,D))
    h=np.array([(6*Dq if n in('x2y2','z2') else -4*Dq) for n in names])
    for (i,j,o,sg) in onebody: H[i,j]+=sg*h[o]
    for (i,j,a,b,c,d,sg) in tb:
        v=Vee[a//2,c//2,b//2,d//2]
        if abs(v)>1e-13: H[i,j]+=0.5*sg*v
    Hs=H[np.ix_(sl,sl)]
    w,v=np.linalg.eigh(Hs+1e4*SS)
    s2=np.einsum('ik,ij,jk->k',v,SS,v)
    t=np.sort(w[np.abs(s2-2)<1e-5])
    g=[t[0]]
    for e in t[1:]:
        if abs(e-g[-1])>0.5: g.append(e)
    return np.array(g)-t[0]
obs=np.array([22900,23730,24580.])
def res(p):
    L=levels(p[0],p[1])
    return L[1:4]-obs
s=least_squares(res,[2600,850],x_scale=[100,50])
print("fit Dq,B =",s.x,"C=",4.3*s.x[1]); print("resid",s.fun)
L=levels(*s.x); print("ground-relative levels (first 8):",np.round(L[:8],0))
