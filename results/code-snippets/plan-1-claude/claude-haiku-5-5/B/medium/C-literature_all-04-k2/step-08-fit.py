import numpy as np, d3
from scipy.optimize import least_squares
def FkOf(B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    return {0:0.0,2:F2,4:F4}
def group(e,tol=1e-5):
    out=[]
    for x in e:
        if out and abs(x-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([x,1])
    return out
def spectrum(Dq,B,C):
    b,H=d3.build(3,FkOf(B,C),Dq)
    up=[i for i,s in enumerate(b) if all(o%2==0 for o in s)]
    qlev=group(np.sort(np.linalg.eigvalsh(H[np.ix_(up,up)])))
    half=[i for i,s in enumerate(b) if sum(1 for o in s if o%2==0)==2]
    rem=list(np.sort(np.linalg.eigvalsh(H[np.ix_(half,half)])))
    for e,m in qlev:
        for _ in range(m):
            j=int(np.argmin([abs(x-e) for x in rem])); rem.pop(j)
    return qlev,group(np.array(rem))
if __name__=="__main__":
    q,d=spectrum(0.0,1000.0,4000.0)
    print("quartets",[(round(e,2),m) for e,m in q])
    print("doublets",[(round(e,2),m) for e,m in d])
