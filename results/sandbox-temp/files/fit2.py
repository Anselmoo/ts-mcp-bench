import numpy as np
from scipy.optimize import least_squares
H1=np.load('H1.npy');H2=np.load('H2.npy')/25;H4=np.load('H4.npy')/25
def uniq(w):
    out=[];cnt=[]
    for x in w:
        if out and abs(x-out[-1])<1e-3: cnt[-1]+=1
        else: out.append(x);cnt.append(1)
    return list(zip(out,cnt))
def lev(Dq,B,C):
    H=Dq*H1+(49*B+7*C)*H2+(441*C/35)*H4
    w=np.linalg.eigvalsh(H); return uniq(w-w[0])
def quartets(Dq,B,C):
    u=lev(Dq,B,C); return [x for x,n in u if n==12][:3]
def doubl(Dq,B,C):
    u=lev(Dq,B,C); return u[1]
print(lev(1750,618,2472)[:6])
obs=[17500,23860,37910]
def r(p):
    Dq,B=p; return np.array(quartets(Dq,B,4*B))-obs
s=least_squares(r,[1750,620]); print(s.x, r(s.x))
Dq,B=s.x
from scipy.optimize import brentq
f=lambda C: doubl(Dq,B,C)[0]-12090
C=brentq(f,1000,5000); print(C, C/B, lev(Dq,B,C)[:6])
