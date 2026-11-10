import numpy as np, d3
from scipy.optimize import brentq
def spectrum(B,C,Dq):
    F4=441*C/35; F2=49*B+5*F4/9
    M=d3.build(F2,F4,Dq)
    # block diag by S: eigen of M restricted to S2 eigenspaces
    out={}
    for S2v,label in [(3.75,'Q'),(0.75,'D')]:
        ev,vec=np.linalg.eigh(d3.S2)
        P=vec[:,np.abs(ev-S2v)<1e-6]
        Mr=P.conj().T@M@P
        e=np.sort(np.linalg.eigvalsh(Mr).real)
        # cluster
        cl=[]
        for x in e:
            if cl and abs(x-cl[-1][0])<0.5: cl[-1][1]+=1
            else: cl.append([x,1])
        out[label]=cl
    return out
if __name__=='__main__':
    s=spectrum(900,3500,2660)
    g=s['Q'][0][0]
    for x,m in s['Q']: print('Q',round(x-g,1),m)
    for x,m in s['D']: print('D',round(x-g,1),m)
