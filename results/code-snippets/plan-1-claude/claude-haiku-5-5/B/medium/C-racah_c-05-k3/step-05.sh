
cat << 'EOF' > d3b.py
import numpy as np, itertools
from scipy.special import eval_legendre
exec(open('d3.py').read().split('n=10; dim=2**n')[0].replace('print("a0','0 and print("a0'))
n=10; dim=2**n
Wr=W
rho_w=rho*W[None,None,:]
def ang(k):
    P=eval_legendre(k,cg)
    R=np.einsum('ikp,pq->ikq',rho_w,P)
    return np.einsum('ikq,jlq->ikjl',R,rho)
A0,A2,A4=ang(0),ang(2),ang(4)
print("a0", A0[0,0,0,0], A0[0,0,1,1], A0[0,1,0,1])
CR=[]
for p in range(n):
    M=np.zeros((dim,dim))
    for s in range(dim):
        if not (s>>p)&1:
            M[s|(1<<p),s]=(-1)**bin(s&((1<<p)-1)).count('1')
    CR.append(M)
AN=[m.T.copy() for m in CR]
Nop=sum(CR[p]@AN[p] for p in range(n)).diagonal()
idx=np.where(np.round(Nop)==3)[0]
Sp=sum(CR[2*o]@AN[2*o+1] for o in range(5))
Sz=0.5*sum(CR[2*o]@AN[2*o]-CR[2*o+1]@AN[2*o+1] for o in range(5))
S2full=(Sp.T@Sp+Sz@Sz+Sz)[np.ix_(idx,idx)]
def spectrum(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    Vt=F2*A2+F4*A4
    eps=[-4*Dq]*3+[6*Dq]*2
    Hf=np.zeros((dim,dim))
    for o in range(5):
        for s in range(2):
            p=2*o+s; Hf+=eps[o]*CR[p]@AN[p]
    for a,b,c,d in itertools.product(range(5),repeat=4):
        v=Vt[a,c,b,d]
        if abs(v)<1e-13: continue
        for s1 in range(2):
            for s2 in range(2):
                p=2*a+s1; q=2*b+s2; r=2*d+s2; s=2*c+s1
                Hf+=0.5*v*CR[p]@CR[q]@AN[r]@AN[s]
    H=Hf[np.ix_(idx,idx)]
    E,V=np.linalg.eigh(H)
    # classify by S2 expectation
    res=[]
    # project: diagonalize H within each S2 eigenspace
    S2e,S2v=np.linalg.eigh(S2full)
    out=[]
    for sv in np.unique(np.round(S2e,6)):
        Vs=S2v[:,np.abs(S2e-sv)<1e-6]
        Hs=Vs.T@H@Vs
        es=np.linalg.eigvalsh(Hs)
        out.append((round(sv*1,3), np.round(es,1)))
    return out
if __name__=="__main__":
    for S,es in spectrum(0.,600.,2400.): print(S, es)
EOF
python3 d3b.py
