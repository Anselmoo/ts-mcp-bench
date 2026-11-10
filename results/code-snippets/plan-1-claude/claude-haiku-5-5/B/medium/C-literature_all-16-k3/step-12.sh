
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
    F2=49*B+7*C; F4=12.6*C
    H=F2*H2+F4*H4
    hm=-4*Dq*Pt+6*Dq*Pe
    for a in range(5):
        for b in range(5):
            if abs(hm[a,b])>1e-14: H=H+hm[a,b]*ONE[(a,b)]
    et=np.sort(np.linalg.eigvalsh(H[np.ix_(iz,iz)]))
    ez=np.sort(np.linalg.eigvalsh(H[np.ix_(i0,i0)]))
    ez=list(ez)
    for t in et:
        j=int(np.argmin(np.abs(np.array(ez)-t))); ez.pop(j)
    return et, np.array(ez)
def uniq(e,tol=1e-3):
    out=[]
    for x in e:
        if out and abs(x-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([x,1])
    return out
et,ez=levels(1000,1000,4000)
print("triplets (Ms=1) with mult:", [(round(a-et[0],1),m) for a,m in uniq(et)])
print("singlets with mult:", [(round(a-et[0],1),m) for a,m in uniq(ez)])
np.set_printoptions(linewidth=150)
import sys
# store as function
def term_energies(Dq,B,C):
    et,ez=levels(Dq,B,C)
    tr=[(a-et[0],m) for a,m in uniq(et)]
    si=[(a-et[0],m) for a,m in uniq(ez)]
    return tr,si
obs={'3T2':7400,'3T1F':12660,'3T1P':23840,'1E':15150}
# fit: 3T2 mult3, 3T1F mult3 , 3T1P mult3 (triplet list), singlet 1E mult2
def model(p):
    Dq,B,C=p
    tr,si=term_energies(Dq,B,C)
    return tr,si
def res(p):
    tr,si=model(p)
    trs=[a for a,m in tr if a>1e-6]
    sis=[a for a,m in si]
    # triplets sorted: 3T2, 3T1F, 3T1P
    r=[trs[0]-7400, trs[1]-12660, trs[2]-23840]
    # 1E candidates: choose the singlet closest to 15150 among 1E-multiplicity-2 levels
    cands=[a for a,m in si if m==2]
    r.append(min(abs(c-15150) for c in cands))
    return np.array(r)
print("trip spectrum at guess:", [(round(a),m) for a,m in model((740,1000,4000))[0]])
sol=least_squares(res,[740,800,3500],x_scale=[100,100,500])
print(sol.x, res(sol.x))
tr,si=model(sol.x)
print("triplets", [(round(a),m) for a,m in tr])
print("singlets", [(round(a),m) for a,m in si])
EOF
