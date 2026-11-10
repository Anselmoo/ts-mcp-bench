import numpy as np, itertools
from scipy.special import sph_harm_y
def sph_harm(m,k,PH,TH): return sph_harm_y(k,m,TH,PH)
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
th=np.arccos(xg); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=(np.outer(wg,np.ones(nphi))*2*np.pi/nphi)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
orbs={'xy':x*y,'xz':x*z,'yz':y*z,'z2':(3*z**2-1)/2,'x2y2':(x**2-y**2)*np.sqrt(3)/2}
names=list(orbs)
for n in names:
    f=orbs[n]; orbs[n]=f/np.sqrt(np.sum(W*f*f))
def Rkq(k):
    out=[]
    for m in range(-k,k+1):
        if m==0: out.append(sph_harm(0,k,PH,TH).real)
        elif m>0: out.append(np.sqrt(2)*(-1)**m*sph_harm(m,k,PH,TH).real)
        else: out.append(np.sqrt(2)*(-1)**m*sph_harm(-m,k,PH,TH).imag)
    return out
def ak(k):
    R=Rkq(k); n=5
    G=np.zeros((n,n,len(R)))
    for i,a in enumerate(names):
        for j,c in enumerate(names):
            for q,Rq in enumerate(R):
                G[i,j,q]=np.sum(W*orbs[a]*orbs[c]*Rq)
    return np.einsum('acq,bdq->abcd',G,G)*4*np.pi/(2*k+1)
A={k:ak(k) for k in (0,2,4)}
print("a0 check", A[0][0,0,0,0], A[0][3,3,3,3])
so=[(o,s) for o in range(5) for s in (0,1)]
N=10
def build(Dq,B,C):
    F4=441*C/35.0; F2=441*B+5*F4
    F={0:0.0,2:F2,4:F4}
    V=np.zeros((N,N,N,N))
    for i,(oi,si) in enumerate(so):
        for j,(oj,sj) in enumerate(so):
            for k_,(ok,sk) in enumerate(so):
                for l,(ol,sl) in enumerate(so):
                    if si!=sk or sj!=sl: continue
                    V[i,j,k_,l]=sum(F[kk]*A[kk][oi,ok,oj,ol] for kk in (0,2,4))
    h=np.zeros((N,N))
    for i,(o,s) in enumerate(so):
        h[i,i]= -4*Dq if o<3 else 6*Dq
    return h,V
dets=list(itertools.combinations(range(N),7))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det,ops):
    occ=list(det); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
ee=[(i,j,k,l) for i,j,k,l in itertools.product(range(N),repeat=4) if so[i][1]==so[k][1] and so[j][1]==so[l][1]]
M=len(dets)
def hamiltonian(Dq,B,C):
    h,V=build(Dq,B,C)
    H=np.zeros((M,M))
    for m,d in enumerate(dets):
        for i in range(N):
            for j in range(N):
                if abs(h[i,j])>1e-12:
                    r,s=apply_ops(d,[('c',i),('a',j)])
                    if r is not None: H[idx[r],m]+=h[i,j]*s
        for (i,j,k,l) in ee:
            v=V[i,j,k,l]
            if abs(v)<1e-12: continue
            r,s=apply_ops(d,[('c',i),('c',j),('a',l),('a',k)])
            if r is not None: H[idx[r],m]+=0.5*v*s
    return H
Sz=np.zeros((M,M)); Sp=np.zeros((M,M))
for m,d in enumerate(dets):
    Sz[m,m]=sum(0.5 if so[i][1]==0 else -0.5 for i in d)
    for o in range(5):
        r,s=apply_ops(d,[('c',2*o),('a',2*o+1)])
        if r is not None: Sp[idx[r],m]+=s
S2=Sz@Sz+0.5*(Sp@Sp.T+Sp.T@Sp)
def levels(Dq,B,C):
    H=hamiltonian(Dq,B,C)
    w,v=np.linalg.eigh(H+1e5*S2)
    res={}
    for e,vec in zip(w,v.T):
        s2=vec@S2@vec; S=(-1+np.sqrt(1+4*s2))/2
        res.setdefault(round(2*S),[]).append(e)
    return res
import pickle
# Save H builder outputs as functions of parameters: linear in Dq, and F2,F4 linear -> compute basis matrices
H0=hamiltonian(0,0,0)   # zero
Hd=hamiltonian(1,0,0)-H0  # Dq coefficient
# Coulomb part linear in F2,F4: compute with B=1,C=0 and B=0,C=1
HB=hamiltonian(0,1,0)-H0
HC=hamiltonian(0,0,1)-H0
def Hfull(Dq,B,C): return H0+Dq*Hd+B*HB+C*HC
def levels_p(Dq,B,C):
    w,v=np.linalg.eigh(Hfull(Dq,B,C)+1e5*S2)
    res={}
    for e,vec in zip(w,v.T):
        s2=vec@S2@vec; S=(-1+np.sqrt(1+4*s2))/2
        res.setdefault(round(2*S),[]).append(e)
    return res
r=levels_p(0,1,0)
print("free ion B only: quartet", [round(x-r[3][0],1) for x in r[3]][:4])
print("doublets", [round(x-r[3][0],1) for x in r[1]][:8])
for Dq,B,C in [(1000,1000,4000)]:
    r=levels_p(Dq,B,C)
    print({k:[round(x,1) for x in v[:6]] for k,v in r.items()})
np.savez('/dev/null',x=1) if False else None
# store matrices in a string for fitting
np.save  # no-op
from scipy.optimize import least_squares
obs={'4T2':8480,'4A2':16305,'4T1P':20360,'2T1':21001}
def predicted(p):
    Dq,B,C=p
    r=levels_p(Dq,B,C)
    q=sorted(set(np.round(r[3],6)))
    d=sorted(r[1])
    return r
r=levels_p(800,900,4000)
q=sorted(r[3]); d=sorted(r[1])
print("quartets",[round(x-q[0],1) for x in q])
print("doublets",[round(x-q[0],1) for x in d])
