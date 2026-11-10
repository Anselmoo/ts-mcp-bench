import numpy as np
from scipy.optimize import least_squares
H2,H4,HD,S2=np.load('m.npy')
def levels(Dq,B,Cr=4.4):
    Cc=Cr*B; F4=441*Cc/35; F2=49*(B+5*F4/441)
    H=F2*H2+F4*H4+Dq*HD
    w,v=np.linalg.eigh(H)
    S=np.einsum('ij,jk,ki->i',v.T,S2,v)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        out.append((w[i],round(np.mean(S[i:j]),2),j-i)); i=j
    return out
if __name__=='__main__':
    for e,s,g in levels(0,1000)[:4]: print(e-levels(0,1000)[0][0],s,g)
    L=levels(3000,600); e0=L[0][0]
    for e,s,g in L[:14]: print(round(e-e0),s,g)
