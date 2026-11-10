import numpy as np
from scipy.optimize import least_squares
H1=np.load('H1.npy');H2=np.load('H2.npy');H4=np.load('H4.npy')
def lev(Dq,B,C):
    F2=49*B+7*C; F4=63*C
    # F2 = F^2/49 etc: Racah B=F2-5F4, C=35F4 with F2=F^2/49,F4=F^4/441
    H=Dq*H1+F2*49*H2/49+0
    H=Dq*H1+(49*B+7*C)*H2+ (441*C/35)*H4
    w=np.linalg.eigvalsh(H); return w-w[0]
def uniq(w):
    out=[];cnt=[]
    for x in w:
        if out and abs(x-out[-1])<1e-3: cnt[-1]+=1
        else: out.append(x);cnt.append(1)
    return list(zip(np.round(out,1),cnt))
print(uniq(lev(1750,618,2472))[:8])
def res(p):
    Dq,B,C=p; u=uniq(lev(Dq,B,C))
    # degeneracies: 4A2(4),2E(4),2T1(6),4T2(12)...
    e={}
    for x,n in u: e.setdefault(n,[]).append(x)
    return u
