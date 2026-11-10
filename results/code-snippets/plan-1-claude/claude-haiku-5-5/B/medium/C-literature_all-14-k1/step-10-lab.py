import numpy as np
import d7
Gam = np.load('Gam.npy')
def labels(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    Hm = sum(Dq*d7.fieldDq[o]*d7.ONEs[o] for o in range(5)) + d7.Ts[0] + F2*d7.Ts[1] + F4*d7.Ts[2]
    s2,Uq = np.linalg.eigh(d7.S2s)
    out=[]
    for S in (1.5,0.5):
        sel = np.abs(s2-S*(S+1))<1e-6
        Us = Uq[:,sel]
        e,V = np.linalg.eigh(Us.T@Hm@Us)
        Gm = Us.T@Gam@Us
        i=0
        while i<len(e):
            j=i
            while j+1<len(e) and abs(e[j+1]-e[i])<1e-6: j+=1
            Vb = V[:,i:j+1]
            chi = np.trace(Vb.T@Gm@Vb)
            out.append((S, e[i], j-i+1, round(chi.real,3)))
            i=j+1
    return out
if __name__=="__main__":
    for S,e,m,chi in labels(1000.,1000.,4000.):
        print(S, round(e,1), m, chi)
