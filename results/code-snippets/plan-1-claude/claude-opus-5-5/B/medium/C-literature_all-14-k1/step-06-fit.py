import numpy as np
from scipy.optimize import fsolve
z=np.load('mats.npz'); H1,H2,H4,S2,ML=[z[k] for k in ('H1','H2','H4','S2','ML')]
N=len(ML)
def levels(Dq,B,C):
    H=Dq*H1+49*(B+C/7)*H2+441*C/35*H4
    e,v=np.linalg.eigh(H); out=[];i=0
    while i<N:
        j=i
        while j<N and e[j]-e[i]<1e-6: j+=1
        V=v[:,i:j]; s2=np.trace(V.T@S2@V)/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        c4=np.real(np.sum(np.abs(V)**2*np.exp(-1j*ML*np.pi/2)[:,None]))/(2*S+1)
        out.append((e[i]-e[0],round(2*S+1),j-i,round(c4))); i=j
    return out
def pick(L,mult,deg,c4,n):
    c=[x[0] for x in L if x[1]==mult and x[2]==deg*mult and x[3]==c4]; return c[n-1]
def f(p):
    L=levels(*p)
    return [pick(L,4,3,-1,1)-8100, pick(L,4,3,1,2)-19400, pick(L,2,3,1,2)-21600]
s=fsolve(f,[810,900,3600]); print(s,f(s))
for l in levels(*s)[:12]: print(l)
