import numpy as np
from scipy.special import sph_harm_y
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),ph,indexing='ij')
W=(wg[:,None]*np.ones(nphi)[None,:])*(2*np.pi/nphi)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
orbs={'xy':x*y,'yz':y*z,'zx':z*x,'x2y2':x*x-y*y,'z2':3*z*z-1}
names=list(orbs)
for n in names:
    orbs[n]=orbs[n]/np.sqrt(np.sum(W*orbs[n]**2))
def realY(l,m,TH,PH):
    if m==0: return sph_harm_y(l,0,TH,PH).real
    if m>0: return np.sqrt(2)*(-1)**m*sph_harm_y(l,m,TH,PH).real
    return np.sqrt(2)*(-1)**m*sph_harm_y(l,-m,TH,PH).imag
def Vang(k):
    Yk=[realY(k,q,TH,PH) for q in range(-k,k+1)]
    M=np.zeros((5,5,len(Yk)))
    for i,a in enumerate(names):
        for j,c in enumerate(names):
            for q,Y in enumerate(Yk):
                M[i,j,q]=np.sum(W*orbs[a]*orbs[c]*Y)
    return np.einsum('acq,bdq->acbd',M,M)*4*np.pi/(2*k+1)
A2=Vang(2);A4=Vang(4)
N=10
states=[s for s in range(1<<N) if bin(s).count('1')==4]
idx={s:i for i,s in enumerate(states)}
D=len(states)
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
# two-body terms list: (a,b,c,d,spatial-indices) with operator c+_a c+_b c_d c_c, coefficient 0.5*V_abcd, V=<ab|cd>
terms=[]
for a in range(N):
 for b in range(N):
  for c in range(N):
   for d in range(N):
    if a%2!=c%2 or b%2!=d%2: continue
    terms.append((a,b,c,d))
def Hmat(Vee,Dq):
    H=np.zeros((D,D))
    h=np.array([(6*Dq if n in('x2y2','z2') else -4*Dq) for n in names])
    for s in states:
        j=idx[s]
        for p in range(N):
            for q in range(N):
                if p%2!=q%2: continue
                hv=h[p//2] if p==q else 0.0
                if p!=q: continue
                if hv==0: continue
                r=cop(s,[('d',p),('c',q)])
                if r: H[idx[r[1]],j]+=r[0]*hv
        for (a,b,c,d) in terms:
            v=Vee[a//2,b//2,d//2,c//2]  # <ab|cd> with orbital indices a(1)->c(1)?? placeholder
            pass
    return H
