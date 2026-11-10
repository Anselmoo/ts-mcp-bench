cd <SANDBOX_TMP>; cat > g.py <<'E'
from a import *
import a
def ident(Dq,B,Cc):
    Hm=a.H(Dq,B,Cc,1)
    w,v=np.linalg.eigh(Hm)
    dets=[d for d in dets_all if sum(1 if p%2==0 else -1 for p in d)==1]
    # orbital R: order xy,yz,z2,xz,x2-y2 ; x->y,y->-x
    R1=np.zeros((5,5)); R1[0,0]=-1; R1[3,1]=-1 ; R1[1,3]=1; R1[2,2]=1; R1[4,4]=-1
    R=np.kron(R1,np.eye(2))
    N=len(dets); Rm=np.zeros((N,N))
    for I,d in enumerate(dets):
        for J,e in enumerate(dets):
            Rm[J,I]=np.linalg.det(R[np.ix_(e,d)])
    out=[];i=0
    w0=w-w[0]
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3:j+=1
        sub=v[:,i:j]; chi=np.trace(sub.conj().T@Rm@sub).real
        out.append((round(w0[i],1),j-i,round(chi,2)));i=j
    return out
if __name__=="__main__":
    for l in ident(814.5,878.1,3500)[:40]: print(l)
E
python3 g.py