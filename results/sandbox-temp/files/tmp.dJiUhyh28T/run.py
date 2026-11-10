exec(open('full.py').read().split('if __name__')[0])
ws,Us=np.linalg.eigh(S2[np.ix_(idx,idx)])
def spectrum(Dq,B,C_):
    H=build_H(Dq,B,C_)[np.ix_(idx,idx)]
    out={}
    for S in [1.5,0.5]:
        sel=np.abs(ws-S*(S+1))<1e-6
        U=Us[:,sel]
        Hsub=U.T@H@U
        out[S]=np.sort(np.linalg.eigvalsh((Hsub+Hsub.T)/2))
    return out
o=spectrum(1,0,0); print({k:v.round(3) for k,v in o.items()})
o=spectrum(0,1,0); print({k:v.round(3) for k,v in o.items()})
