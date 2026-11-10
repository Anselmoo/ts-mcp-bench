import numpy as np
from scipy.optimize import least_squares
M=np.load('<SANDBOX_TMP>/m.npz')
def levels(Dq,B,C):
    H=Dq*M['Hd']+(49*B+7*C)*M['F2']+12.6*C*M['F4']
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        P=v[:,i:j]
        S2=np.real(np.trace(P.T@M['S2']@P))/(j-i); S=(-1+np.sqrt(1+4*S2))/2
        mult=int(round(2*S+1)); g=(j-i)//mult
        ch=np.real(np.trace(P.conj().T@M['C4']@P))/mult
        lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}[g].get(int(round(ch)),'?')
        out.append((w[i],f"{mult}{lab}"));i=j
    E0=out[0][0]
    return [(e-E0,l) for e,l in out]
def pick(L,lab,k):
    return [e for e,l in L if l==lab][k-1]
obs=[7150,15200,19200,21130]
def res(p):
    L=levels(*p)
    return np.array([pick(L,'4T2',1),pick(L,'4A2',1),pick(L,'4T1',2),pick(L,'2T1',2)])-obs
r=least_squares(res,[800,850,3500])
print(r.x,res(r.x))
for e,l in levels(*r.x)[:14]: print(round(e),l)
print(levels(*r.x)[0])
