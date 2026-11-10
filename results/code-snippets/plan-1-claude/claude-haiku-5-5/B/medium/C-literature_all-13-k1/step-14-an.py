import numpy as np
from scipy.optimize import least_squares
d=np.load('mats.npz'); Hc,H2,H4,S2,ML=d['Hc'],d['H2'],d['H4'],d['S2'],d['ML']
MLi=np.round(ML).astype(int)
blocks=[np.where(MLi%4==r)[0] for r in range(4)]
def levels(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    H=Dq*Hc+F2*H2+F4*H4
    out=[]  # (E, S, r, count)
    for r,idx in enumerate(blocks):
        Hb=H[np.ix_(idx,idx)]; Sb=S2[np.ix_(idx,idx)]
        w,v=np.linalg.eigh(Hb+1e5*Sb)
        for vec in v.T:
            s2=vec@Sb@vec; S=(-1+np.sqrt(1+4*s2))/2
            out.append((vec@Hb@vec, round(2*S)/2, r))
    # cluster by (S,E)
    out.sort(key=lambda x:(x[1],x[0]))
    levs=[]
    for E,S,r in out:
        if levs and levs[-1]['S']==S and abs(levs[-1]['E']-E)<0.05:
            levs[-1]['cnt'][r]+=1
        else:
            cnt=[0,0,0,0]; cnt[r]=1
            levs.append({'E':E,'S':S,'cnt':cnt})
    # orbital dim and C4 character
    res=[]
    for L in levs:
        mult=int(round(2*L['S']+1))
        dimorb=sum(L['cnt'])//mult
        tr=sum(L['cnt'][r]*(1j)**(-r) for r in range(4))/mult
        res.append((L['E'],L['S'],dimorb,np.round(tr,3)))
    return res
if __name__=="__main__":
    for x in levels(800,900,3500): print(round(x[0],1),x[1],x[2],x[3])
