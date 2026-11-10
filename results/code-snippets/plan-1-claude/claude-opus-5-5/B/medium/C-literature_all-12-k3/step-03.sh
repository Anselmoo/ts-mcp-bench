
cd <SANDBOX_TMP>/tmp.18wMokKLZh
cat << 'EOF' > d7.py
import numpy as np, itertools, functools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]; so=[(m,s) for m in ml for s in (0,1)]
@functools.lru_cache(None)
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
idx={m:i for i,m in enumerate(ml)}
V=np.zeros((5,5))
for m,v in zip(ml,[1,-4,6,-4,1]): V[idx[m],idx[m]]=v
V[idx[2],idx[-2]]=V[idx[-2],idx[2]]=5
dets=[d for d in itertools.combinations(range(10),7) if np.isclose(sum(0.5 if so[p][1] else -0.5 for p in d),0.5) or np.isclose(sum(0.5 if so[p][1] else -0.5 for p in d),1.5)]
dind={d:i for i,d in enumerate(dets)}; N=len(dets)
def ops():
    H1=np.zeros((N,N)); H2={2:np.zeros((N,N)),4:np.zeros((N,N))}
    for i,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[idx[so[q][0]],idx[so[p][0]]]
                if v==0 or (q!=p and q in d): continue
                nd=list(d); pos=nd.index(p); sign=(-1)**pos; nd.pop(pos)
                k=sum(1 for x in nd if x<q); sign*=(-1)**k; nd.insert(k,q)
                H1[dind[tuple(nd)],i]+=sign*v
        for a,b in itertools.combinations(d,2):
            for r in range(10):
                for s in range(10):
                    if r==s or so[r][1]!=so[a][1] or so[s][1]!=so[b][1]: continue
                    if so[r][0]+so[s][0]!=so[a][0]+so[b][0]: continue
                    nd=list(d); sign=1
                    pb=nd.index(b); sign*=(-1)**pb; nd.pop(pb)
                    pa=nd.index(a); sign*=(-1)**pa; nd.pop(pa)
                    if s in nd or r in nd: continue
                    k=sum(1 for x in nd if x<s); sign*=(-1)**k; nd.insert(k,s)
                    k=sum(1 for x in nd if x<r); sign*=(-1)**k; nd.insert(k,r)
                    j=dind[tuple(nd)]
                    for kk in (2,4):
                        H2[kk][j,i]+=sign*c(kk,so[r][0],so[a][0])*c(kk,so[b][0],so[s][0])
    return H1,H2
H1,H2=ops()
Sz=np.array([sum(0.5 if so[p][1] else -0.5 for p in d) for d in dets])
ML=np.array([sum(so[p][0] for p in d) for d in dets])
rot=np.exp(1j*np.pi/2*ML)
def H(Dq,B,C): return Dq*H1+(49*B+7*C)*H2[2]+(441*C/35)*H2[4]
def levels(Dq,B,C):
    Hm=H(Dq,B,C); res=[]
    q=np.where(Sz==1.5)[0]; eq=np.linalg.eigvalsh(Hm[np.ix_(q,q)])
    ii=np.where(Sz==0.5)[0]; w,v=np.linalg.eigh(Hm[np.ix_(ii,ii)])
    # group
    i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        deg=j-i; ch=np.real(np.sum(np.conj(v[:,i:j])*(rot[ii][:,None]*v[:,i:j])))
        nq=np.sum(np.abs(eq-w[i])<1e-3)
        res.append((w[i],deg,ch,nq)); i=j
    return res
def label(r):
    e,deg,ch,nq=r
    spin=4 if nq>0 else 2
    orb=deg//(2 if spin==4 else 1)
    # if quartet, Sz=1/2 subspace holds orb states; but char also includes nothing else
    sym={1:{1:'A1',-1:'A2'},2:{2:'E'},3:{1:'T1',-1:'T2'}}
    c=round(ch); 
    lab=sym.get(orb,{}).get(c,'?') if orb!=2 else 'E'
    return spin,lab
def table(Dq,B,C):
    L=levels(Dq,B,C); E0=L[0][0]; out=[]
    for r in L:
        s,l=label(r); out.append((r[0]-E0,f"{s}{l}"))
    return out
if __name__=="__main__":
    for e,l in table(625,800,3200)[:20]: print(round(e),l)
EOF
python3 d7.py
