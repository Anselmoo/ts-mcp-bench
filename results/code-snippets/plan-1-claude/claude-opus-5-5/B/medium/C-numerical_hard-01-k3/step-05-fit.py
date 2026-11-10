import numpy as np
from scipy.optimize import least_squares
d=np.load('mats.npz'); VCF,G2,G4,S2=d['VCF'],d['G2'],d['G4'],d['S2']
def levels(Dq,B,C):
    H=Dq*VCF+(49*B+7*C)*G2+(441*C/35)*G4 + 1e6*0  
    w,v=np.linalg.eigh(H+1e-3*S2*0)
    s=np.einsum('ij,jk,ki->i',v.T,S2,v)
    # group
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        S=np.mean(s[i:j]); out.append((w[i],round((-1+np.sqrt(1+4*S))/2,2),j-i)); i=j
    return out
def trip(Dq,B,r=4.7):
    L=levels(Dq,B,r*B); g=L[0]
    tr=[(e-L[0][0],S,n) for e,S,n in L if abs(S-1)<0.05]
    return L[0],tr
if __name__=='__main__':
    print(trip(3000,600)[0]); print(trip(3000,600)[1][:6])
