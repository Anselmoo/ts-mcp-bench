from ts import *
B=806.;Cc=3570.
def Hx(x): return H2[2]*(49*B+7*Cc)+H2[4]*12.6*Cc+H1*x*B
for x in (0.001,0.5,1.0):
    w,v=np.linalg.eigh(Hx(x));i=0
    while i<n:
        j=i
        while j<n and abs(w[j]-w[i])<1e-6*B: j+=1
        P=v[:,i:j];deg=j-i
        s2=np.trace(P.T@S2@P).real/deg; S=(-1+np.sqrt(1+4*s2))/2; m=int(round(2*S+1))
        c4=np.trace(P.conj().T@R4@P).real/m; c2=np.trace(P.conj().T@R2@P).real/m
        if abs(c4-round(c4))>1e-4 or deg%m or (round(c4),round(c2)) not in [(1,1),(-1,-1),(0,0),(1,-1),(-1,1)]: print(x,w[i]/B,deg,m,c4,c2)
        i=j
