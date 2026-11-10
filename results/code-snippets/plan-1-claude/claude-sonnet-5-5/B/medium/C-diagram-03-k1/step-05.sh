cd <SANDBOX_TMP> && python3 - <<'E'
import re
s=open('a.py').read()
s=s[:s.index("lab={")]
s+='''
import itertools,json
dims={'A1':(1,1,1),'A2':(1,-1,1),'E':(2,0,2),'T1':(3,1,-1),'T2':(3,-1,-1)}
def decomp(n,c4,c2):
    best=None
    for m in itertools.product(range(4),repeat=5):
        if sum(k*dims[t][0] for k,t in zip(m,dims))!=n:continue
        if sum(k*dims[t][1] for k,t in zip(m,dims))!=c4:continue
        if sum(k*dims[t][2] for k,t in zip(m,dims))!=c2:continue
        if best is None or sum(m)<sum(best):best=m
    return [t for k,t in zip(best,dims) for _ in range(k)]
C2=C4@C4
allr={}
for Dq in np.arange(0,4.01,.5):
    D=Dq*B+(1.0 if Dq==0 else 0)
    w,v=np.linalg.eigh(Hc+D*H1);w-=w[0]
    out=[];i=0
    while i<len(w):
        j=i
        while j+1<len(w) and w[j+1]-w[i]<0.01:j+=1
        U=v[:,i:j+1];n=j-i+1
        s2=np.trace(U.T@S2@U)/n
        c4=round(np.trace(U.conj().T@C4@U).real);c2=round(np.trace(U.conj().T@C2@U).real)
        S=round(-1+np.sqrt(1+4*s2))
        for t in decomp(n,c4,c2):out.append((round(float(w[i])/B,3),f"{S+1 if False else round((-1+np.sqrt(1+4*s2))+1)*1}".replace('.0','')+t+'g'))
        i=j+1
    out=out[:12]
    allr[Dq]=out
    print(Dq,out[:7])
import pickle;pickle.dump(allr,open('r.pkl','wb'))
'''
open('b.py','w').write(s)
E
python3 b.py