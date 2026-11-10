import numpy as np, itertools
from scipy.optimize import brentq, fsolve
from scipy.special import eval_legendre
# grid on sphere
nt, nph = 24, 48
x, wt = np.polynomial.legendre.leggauss(nt)
pts=[]; W=[]
for ct,w in zip(x,wt):
    st=np.sqrt(1-ct*ct)
    for k in range(nph):
        ph=2*np.pi*k/nph
        pts.append([st*np.cos(ph), st*np.sin(ph), ct]); W.append(w*2*np.pi/nph)
P=np.array(pts); W=np.array(W)
X,Y,Z=P.T
# real d angular functions (unnormalized), t2g: xy,yz,xz ; eg: 3z2-1, x2-y2
f=np.array([X*Y, Y*Z, X*Z, (3*Z*Z-1)/2*np.sqrt(3)*0+ (3*Z*Z-1), X*X-Y*Y])
# normalize
for i in range(5):
    f[i]/=np.sqrt(np.sum(W*f[i]**2))
# orthogonality check
G=np.array([[np.sum(W*f[i]*f[j]) for j in range(5)] for i in range(5)])
assert np.allclose(G,np.eye(5),atol=1e-10), G
cosg=P@P.T
Wm=W[:,None]*W[None,:]
Tk={}
for k in [0,2,4]:
    Pk=eval_legendre(k,cosg)
    # T[a,c,b,d] = sum_ij W_i W_j f_a(i) f_c(i) f_b(j) f_d(j) P_k
    A=np.einsum('ai,ci,i,ij->acj',f,f,W,Pk)  # not used
    T=np.zeros((5,5,5,5))
    M=np.einsum('ai,ci->aci',f,f)  # (a,c,i)
    for a in range(5):
        for c in range(5):
            for b in range(5):
                for d in range(5):
                    T[a,c,b,d]=np.einsum('i,j,ij->',W*M[a,c]*0+W*M[a,c],W*f[b]*f[d],Pk)
    Tk[k]=T
# spin orbitals: idx = 2*orb + spin
def V(p,q,r,s,F):
    # <pq|V|rs>
    op,sp=divmod(p,2); oq,sq=divmod(q,2); orr,sr=divmod(r,2); os_,ss=divmod(s,2)
    if sp!=sr or sq!=ss: return 0.0
    return sum(F[k]*Tk[k][op,orr,oq,os_] for k in [0,2,4])
def energies(Dq,B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    eps=np.array([-4*Dq if o in (0,1,2) else 6*Dq for o in range(5)])
    dets=list(itertools.combinations(range(10),2))
    n=len(dets)
    H=np.zeros((n,n))
    for I,(i,j) in enumerate(dets):
        for J,(k,l) in enumerate(dets):
            val=V(i,j,k,l,F)-V(i,j,l,k,F)
            if I==J: val+= eps[i//2]+eps[j//2]
            H[I,J]=val
    # Ms=1 sector: both spin up (spin index 0)
    up=[I for I,(i,j) in enumerate(dets) if i%2==0 and j%2==0]
    Hup=H[np.ix_(up,up)]
    Eup=np.sort(np.linalg.eigvalsh(Hup))
    # Ms=0 sector
    z=[I for I,(i,j) in enumerate(dets) if i%2!=j%2]
    Hz=H[np.ix_(z,z)]
    Ez=np.sort(np.linalg.eigvalsh(Hz))
    return Eup, Ez
if __name__=="__main__":
    Eup,Ez=energies(1000,500,2000)
    print(np.round(Eup-Eup[0],1))
    print(np.round(Ez-Eup[0],1))
