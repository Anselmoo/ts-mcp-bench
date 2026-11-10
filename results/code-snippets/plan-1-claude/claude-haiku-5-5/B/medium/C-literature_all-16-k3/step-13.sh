
cat << 'EOF' | python3 -
import numpy as np
from scipy.special import sph_harm_y as SY
from scipy.optimize import least_squares
nth, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nth)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
ms = list(range(-2,3))
Ylm = {m: SY(2,m,TH,PH) for m in ms}
def ang_k(k):
    A = np.zeros((5,5,5,5), complex)
    for q in range(-k,k+1):
        Yq = SY(k,q,TH,PH)
        P1 = np.array([[np.sum(W*np.conj(Ylm[a])*np.conj(Yq)*Ylm[c]) for c in ms] for a in ms])
        P2 = np.array([[np.sum(W*np.conj(Ylm[b])*Yq*Ylm[d]) for d in ms] for b in ms])
        A += (4*np.pi/(2*k+1))*np.einsum('ac,bd->abcd', P1, P2)
    return A.real
A = {k:ang_k(k) for k in (0,2,4)}
states = [st for st in range(1<<10) if bin(st).count('1')==8]
index = {st:i for i,st in enumerate(states)}; n=len(states)
def ann(i,st):
    if not (st>>i)&1: return None
    return (-1)**bin(st & ((1<<i)-1)).count('1'), st ^ (1<<i)
def cre(i,st):
    if (st>>i)&1: return None
    return (-1)**bin(st & ((1<<i)-1)).count('1'), st | (1<<i)
def op2(a,b,c,d):
    M = np.zeros((n,n))
    for st in states:
        r=ann(c,st)
        if r is None: continue
        s1,t=r; r=ann(d,t)
        if r is None: continue
        s2,t=r; r=cre(b,t)
        if r is None: continue
        s3,t=r; r=cre(a,t)
        if r is None: continue
        s4,t=r
        M[index[t],index[st]] += s1*s2*s3*s4
    return M
so=lambda o,s: 2*o+s
def Hee(Am):
    H=np.zeros((n,n))
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        v=Am[a,b,c,d]
        if abs(v)<1e-12: continue
        for s in (0,1):
         for t in (0,1):
          H += 0.5*v*op2(so(a,s),so(b,t),so(c,s),so(d,t))
    return H
H2=Hee(A[2]); H4=Hee(A[4])
def one(a,b):
    M=np.zeros((n,n))
    for s in (0,1):
        for st in states:
            r=ann(so(b,s),st)
            if r is None: continue
            s1,t=r; r=cre(so(a,s),t)
            if r is None: continue
            s2,t=r
            M[index[t],index[st]] += s1*s2
    return M
ONE={(a,b):one(a,b) for a in range(5) for b in range(5)}
s2=np.sqrt(2)
v_xy=np.zeros(5,complex); v_xy[4]=1/(1j*s2); v_xy[0]=-1/(1j*s2)
v_xz=np.zeros(5,complex); v_xz[3]=-1/s2; v_xz[1]=1/s2
v_yz=np.zeros(5,complex); v_yz[3]=1j/s2; v_yz[1]=1j/s2
v_z2=np.zeros(5,complex); v_z2[2]=1
v_x2=np.zeros(5,complex); v_x2[4]=1/s2; v_x2[0]=1/s2
Pt=sum(np.outer(v,v.conj()) for v in (v_xy,v_xz,v_yz))
Pe=sum(np.outer(v,v.conj()) for v in (v_z2,v_x2))
Sz=np.array([sum(((st>>(2*o))&1)-((st>>(2*o+1))&1) for o in range(5)) for st in states])
iz=np.where(Sz==2)[0]; i0=np.where(Sz==0)[0]
def levels(Dq,B,C):
    H=(49*B+7*C)*H2+12.6*C*H4
    hm=-4*Dq*Pt+6*Dq*Pe
    for a in range(5):
        for b in range(5):
            if abs(hm[a,b])>1e-14: H=H+hm[a,b]*ONE[(a,b)]
    et=np.sort(np.linalg.eigvalsh(H[np.ix_(iz,iz)]))
    ez=list(np.sort(np.linalg.eigvalsh(H[np.ix_(i0,i0)])))
    for t in et:
        j=int(np.argmin(np.abs(np.array(ez)-t))); ez.pop(j)
    return et, np.array(ez)
def spec(Dq,B,C):
    et,ez=levels(Dq,B,C)
    E0=et[0]
    trip=sorted(set(np.round(et-E0,4)))
    # collapse multiplicities
    def collapse(e):
        out=[]
        for x in np.sort(e):
            if out and abs(x-out[-1][0])<1e-3: out[-1][1]+=1
            else: out.append([x,1])
        return out
    return [(a,m) for a,m in collapse(et-E0)], [(a,m) for a,m in collapse(ez-E0)]
Dq=740.0
def res(p):
    B,C=p
    tr,si=spec(Dq,B,C)
    trs=[a for a,m in tr if a>1e-6]
    e1=[a for a,m in si if m==2]
    return np.array([trs[1]-12660, trs[2]-23840, e1[0]-15150])
sol=least_squares(res,[900,4000])
print("Dq=740 fit B,C:", sol.x, "C/B", sol.x[1]/sol.x[0], "resid", res(sol.x))
tr,si=spec(Dq,*sol.x)
print("triplets:", [(round(a,1),m) for a,m in tr])
print("singlets:", [(round(a,1),m) for a,m in si])
EOF
