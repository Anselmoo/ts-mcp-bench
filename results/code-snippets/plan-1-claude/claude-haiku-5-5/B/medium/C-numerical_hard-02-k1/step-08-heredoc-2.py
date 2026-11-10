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
    return np.einsum('acq,bdq->acbd',M,M)*4*np.pi/(2*k+1)   # chemist (ac|bd)
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
# spin-orbital terms for 1/2 sum V_abcd c+_a c+_b c_d c_c, V_abcd = (ac|bd)
terms=[]
for a in range(N):
 for b in range(N):
  for c in range(N):
   for d in range(N):
    if a%2!=c%2 or b%2!=d%2: continue
    v=(A2,A4)
    terms.append((a,b,c,d))
S2=np.zeros((D,D))
Sp=np.zeros((D,D))
for s in states:
    for o in range(5):
        r=cop(s,[('d',2*o),('c',2*o+1)])
        if r: Sp[idx[r[1]],idx[s]]+=r[0]
Sz=np.array([0.5*sum(((s>>(2*o))&1)-((s>>(2*o+1))&1) for o in range(5)) for s in states])
S2=np.diag(Sz**2)+0.5*(Sp@Sp.T+Sp.T@Sp)
def Hmat(B,C,Dq):
    F4=C*441/35.0
    F2=(B*441+5*F4)/9.0
    Vee=F2*A2+F4*A4
    H=np.zeros((D,D))
    h=np.array([(6*Dq if n in('x2y2','z2') else -4*Dq) for n in names])
    for s in states:
        j=idx[s]
        for p in range(N):
            r=cop(s,[('d',p),('c',p)])
            if r: H[idx[r[1]],j]+=r[0]*h[p//2]
        for (a,b,c,d) in terms:
            v=Vee[a//2,c//2,b//2,d//2]
            if abs(v)<1e-13: continue
            r=cop(s,[('c',c),('c',d),('d',b),('d',a)])
            if r: H[idx[r[1]],j]+=0.5*r[0]*v
    return H
def levels(B,C,Dq):
    H=Hmat(B,C,Dq)
    w,v=np.linalg.eigh(H+1e6*S2)
    out=[]
    for k in range(D):
        if abs(v[:,k]@S2@v[:,k]-2)<1e-5: out.append((w[k]-1e6*2))
    # group
    out=np.sort(np.array(out))
    return out
# test: Dq=0 free ion triplets relative
L=levels(800,4.3*800,0.0)
print("free-ion-ish triplet levels (B=800,C=3440,Dq=0):",np.round(L-L[0],0)[:20], len(L))
