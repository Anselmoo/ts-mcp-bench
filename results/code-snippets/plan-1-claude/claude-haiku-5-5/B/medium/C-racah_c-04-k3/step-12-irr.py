import numpy as np, d3, fit
from scipy.linalg import expm
l=2; ms=np.arange(-2,3)
Jz=np.diag(ms).astype(complex)
Jp=np.zeros((5,5),complex)
for i,m in enumerate(ms[:-1]):
    Jp[i+1,i]=np.sqrt(l*(l+1)-m*(m+1))
Jm=Jp.conj().T
Jx=(Jp+Jm)/2; Jy=(Jp-Jm)/(2j)
def manybody(Jn):
    G=np.zeros((120,120),complex)
    for m in range(5):
        for mp in range(5):
            if abs(Jn[m,mp])<1e-12: continue
            for s in (0,1):
                G+=Jn[m,mp]*d3.restrict(d3.cd[2*m+s]@d3.c[2*mp+s])
    return G
def rot(n,theta):
    n=np.array(n,float); n/=np.linalg.norm(n)
    Jn=n[0]*Jx+n[1]*Jy+n[2]*Jz
    return expm(-1j*theta*manybody(Jn))
U_C3=rot([1,1,1],2*np.pi/3)
U_C4=rot([0,0,1],np.pi/2)
U_C2=rot([0,0,1],np.pi)
def analyze(Dq,B,C,tol=0.5):
    H=d3.build_H(Dq,B,C)
    out=[]
    for lab,U in [('D',fit.D),('Q',fit.Q)]:
        Hs=U.conj().T@H@U
        w,v=np.linalg.eigh(Hs)
        Vb=U@v   # physical eigvecs in sector basis (120-dim)
        # group degenerate
        i=0
        while i<len(w):
            j=i
            while j+1<len(w) and abs(w[j+1]-w[i])<tol: j+=1
            Vg=Vb[:,i:j+1]
            d=j-i+1
            chars=[np.trace(Vg.conj().T@Ux@Vg).real for Ux in (U_C3,U_C4,U_C2)]
            out.append((lab,round(w[i],1),d,np.round(chars,2)))
            i=j+1
    return out
if __name__=="__main__":
    for row in analyze(1743,780,3500):
        if row[0]=='D': print(row)
