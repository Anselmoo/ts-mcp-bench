import numpy as np
from scipy.optimize import fsolve
d=np.load('mats.npz')
M2,M4,Heg,H0,S2=d['M2'],d['M4'],d['Hcf_eg'],d['Hcf_0'],d['S2']
CF=-4*H0+10*Heg
def levels(Dq,B,CB=4.5,lam=1000.0):
    C=CB*B
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=Dq*CF+F2*M2+F4*M4+lam*S2
    w,v=np.linalg.eigh(H)
    # singlets: S2 eigenvalue 0 -> energy shifted by lam*0; triplet +2lam, quintet +6lam
    sel=[]
    s2diag=np.einsum('ij,ik,kj->j',v,S2,v)
    for e,s in zip(w,s2diag):
        if abs(s)<0.5: sel.append(e)
    return np.array(sel)
def cluster(e,tol=1.0):
    groups=[]
    for x in e:
        if groups and abs(x-groups[-1][-1])<tol: groups[-1].append(x)
        else: groups.append([x])
    return [(np.mean(g),len(g)) for g in groups]
if __name__=='__main__':
    e=levels(1000.0,700.0)
    print([(round(a-min(e),1),n) for a,n in cluster(e-min(e)+0)][:12])
    print("cluster list (E-E0, deg) singlets:")
    g=cluster(e)
    E0=g[0][0]
    for a,n in g[:10]: print(round(a-E0,1),n)
