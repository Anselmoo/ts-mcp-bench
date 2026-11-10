cd /tmp && cat > /tmp/chk.py << 'EOF'
import numpy as np, itertools
exec(open('/dev/stdin').read()) if False else None
EOF
python3 - << 'EOF'
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre
Bv=1.0; Cb=4.4
F2=49+7*Cb; F4=12.6*Cb
nu,nphi=20,40
u,wu=leggauss(nu); phi=np.arange(nphi)*2*np.pi/nphi
U,PH=np.meshgrid(u,phi,indexing='ij'); st=np.sqrt(1-U**2)
P=np.stack([(st*np.cos(PH)).ravel(),(st*np.sin(PH)).ravel(),U.ravel()],1)
W=(np.outer(wu,np.full(nphi,2*np.pi/nphi))).ravel()
def orbs(p):
    x,y,z=p[:,0],p[:,1],p[:,2]
    return np.stack([x*y,y*z,z*x,x*x-y*y,2*z*z-x*x-y*y],0)
F=orbs(P); F=F/np.sqrt((F**2*W).sum(1))[:,None]
cg=P@P.T
Gk={}
for k in (0,2,4):
    Pk=eval_legendre(k,np.clip(cg,-1,1))
    Gk[k]=np.einsum('acp,pq,bdq->abcd',np.einsum('ap,cp->acp',F*W,F),Pk*W[None,:],np.einsum('bq,dq->bdq',F,F),optimize=True)
Vint=Gk[0]*0+F2*Gk[2]+F4*Gk[4]
NS=10
def run(n):
    states=list(itertools.combinations(range(NS),n)); idx={s:i for i,s in enumerate(states)}; D=len(states)
    def ap(ops,occ):
        occ=list(occ); sg=1
        for t,k in reversed(ops):
            nb=sum(1 for o in occ if o<k)
            if t=='a':
                if k not in occ: return None,0
                occ.remove(k); sg*=(-1)**nb
            else:
                if k in occ: return None,0
                occ.append(k); sg*=(-1)**nb; occ.sort()
        return tuple(occ),sg
    H=np.zeros((D,D))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        if abs(Vint[a,b,c,d])<1e-14: continue
        for s1 in range(2):
            for s2 in range(2):
                i,j,k,l=2*a+s1,2*b+s2,2*c+s1,2*d+s2
                for jj,s in enumerate(states):
                    new,sg=ap([('c',i),('c',j),('a',l),('a',k)],s)
                    if new is not None: H[idx[new],jj]+=0.5*sg*Vint[a,b,c,d]
    Sp1=np.zeros((D,D))
    S2=None
    return states,H
st2,H2=run(2)
# S^2 for d2
states=st2; D=len(states); idx={s:i for i,s in enumerate(states)}
def Sop(n):
    pass
ev=np.linalg.eigvalsh(H2)
print(np.round(np.unique(np.round(ev,6)),4))
EOF