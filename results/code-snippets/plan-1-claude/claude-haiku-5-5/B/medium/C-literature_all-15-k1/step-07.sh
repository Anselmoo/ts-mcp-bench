cd /; python3 - << 'EOF'
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
def mats(B_,C_):
    pass
def op_matrix(Vfun):
    H=np.zeros((M,M))
    for m,d in enumerate(dets):
        for (i,j,k,l,v) in Vfun:
            r,s=apply_ops(d,[('c',i),('c',j),('a',l),('a',k)])
            if r is not None: H[idx[r],m]+=0.5*v*s
    return H
def onebody(hdiag):
    H=np.zeros((M,M))
    for m,d in enumerate(dets):
        for i in range(N):
            r,s=apply_ops(d,[('c',i),('a',i)])
            if r is not None: H[idx[r],m]+=hdiag[i]*s
    return H
hd=np.array([-4.0 if o<3 else 6.0 for o,s in so])
Hcf=onebody(hd)   # coefficient of Dq
# Coulomb parts: separate F2 and F4 pieces
def coul(k):
    Vk=[]
    for (i,j,kk,l) in ee:
        v=A[k][so[i][0],so[kk][0],so[j][0],so[l][0]]
        if abs(v)>1e-12: Vk.append((i,j,kk,l,v))
    return op_matrix(Vk)
H2=coul(2); H4=coul(4); H0c=coul(0)
# sanity: F0 term should be constant (A) across all states
Sz=np.zeros((M,M)); Sp=np.zeros((M,M))
for m,d in enumerate(dets):
    Sz[m,m]=sum(0.5 if so[i][1]==0 else -0.5 for i in d)
    for o in range(5):
        r,s=apply_ops(d,[('c',2*o),('a',2*o+1)])
        if r is not None: Sp[idx[r],m]+=s
S2=Sz@Sz+0.5*(Sp@Sp.T+Sp.T@Sp)
w,U=np.linalg.eigh(S2)
def proj(S):
    val=S*(S+1)
    sel=U[:,np.abs(w-val)<1e-6]
    return sel
def term_energies(Dq,B,C):
    F4=441*C/35.0; F2=441*B+5*F4
    H=Dq*Hcf+F2*H2+F4*H4
    out={}
    for S2v,name in [(1.5,3),(0.5,1)]:
        Q=proj(S2v); Hs=Q.T@H@Q
        out[name]=np.sort(np.linalg.eigvalsh(Hs))
    return out
# Free-ion check: Dq=0 -> levels relative to lowest quartet
t=term_energies(0,1,0)
q=t[3]; print("quartet free-ion (B=1,C=0):", np.round(q-q[0],3))
t=term_energies(0,0,1)
q=t[3]; print("quartet free-ion (C=1,B=0):", np.round(q-q[0],3))
print("Dq-only quartets:", np.round(term_energies(1,0,0)[3],3))
print("Dq-only doublets:", np.round(term_energies(1,0,0)[1],3))
import pickle
pickle.dump({'Hcf':Hcf,'H2':H2,'H4':H4,'S':None}, open('/dev/null','wb')) if False else None
# save via print of params for fitting in same script
from scipy.optimize import least_squares
obs=np.array([8480,16305,20360,21001],float)
# assignment: quartets sorted: indices of observed levels among quartets (4T2,4A2,4T1P) and doublet 2T1(2)
def model_levels(p):
    Dq,B,C=p
    t=term_energies(Dq,B,C)
    return t
def resid(p,which):
    t=model_levels(p)
    q=t[3]; d=t[1]
    # relative to ground 4T1(F) (lowest quartet)
    g=q[0]
    pred=[q[which[0]]-g, q[which[1]]-g, q[which[2]]-g, d[which[3]]-g]
    return np.array(pred)-obs
import itertools as it
best=None
print("quartet levels for trial (900,900,4000):", np.round(term_energies(900,900,4000)[3]-term_energies(900,900,4000)[3][0],0))
print("doublets:", np.round(term_energies(900,900,4000)[1]-term_energies(900,900,4000)[3][0],0))
EOF