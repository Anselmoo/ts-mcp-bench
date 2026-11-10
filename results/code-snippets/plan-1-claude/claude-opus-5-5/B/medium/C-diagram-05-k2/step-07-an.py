import numpy as np
z=np.load('<SANDBOX_TMP>/H.npz'); Hee,Hcf,S2,L2,ML=[z[k] for k in ('Hee','Hcf','S2','L2','ML')]
B=859.
# free ion: diagonalize Hee + small S2,L2 to separate
w,v=np.linalg.eigh(Hee)
cl=[]
i=0
while i<len(w):
    j=i
    while j<len(w) and w[j]-w[i]<1e-3: j+=1
    P=v[:,i:j]; s=np.trace(P.T@S2@P)/(j-i); l=np.trace(P.T@L2@P)/(j-i)
    cl.append((w[i],j-i,s,l)); i=j
E0=cl[0][0]
for e,n,s,l in cl: print(round((e-E0)/B,4),n,round(s,3),round(l,3))
