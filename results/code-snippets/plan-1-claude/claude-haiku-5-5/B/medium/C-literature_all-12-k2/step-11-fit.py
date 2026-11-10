import numpy as np
from scipy.optimize import least_squares
d=np.load('d7mats.npz'); Hcf=d['Hcf']; H2=d['H2']; H4=d['H4']; basis=d['basis']
nup=np.array([sum(1 for o in s if o%2==0) for s in basis])
ndn=7-nup
sec={k:np.where(nup-ndn==k)[0] for k in (3,1)}
def levels(Dq,B,C):
    F2=49*B+5*C; F4=12.6*C
    H=Dq*Hcf+F2*H2+F4*H4
    q=np.linalg.eigvalsh(H[np.ix_(sec[3],sec[3])])
    s=np.linalg.eigvalsh(H[np.ix_(sec[1],sec[1])])
    # remove quartet levels from Sz=1/2 spectrum
    d_=list(s)
    for x in q:
        i=int(np.argmin([abs(y-x) for y in d_])); d_.pop(i)
    return np.sort(q), np.sort(np.array(d_))
if __name__=="__main__":
    q,dd=levels(1000,1000,4000)
    print("quartets",np.round(np.unique(np.round(q,3)),1), np.round(np.unique(np.round(q,3),return_counts=True)[1]))
    v,c=np.unique(np.round(dd,2),return_counts=True)
    print("doublets",list(zip(np.round(v,1),c)))
