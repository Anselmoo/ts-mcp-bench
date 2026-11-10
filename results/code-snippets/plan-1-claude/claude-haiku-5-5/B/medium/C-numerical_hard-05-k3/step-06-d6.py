
Sp=sum(cd[p]@c[p+1] for p in range(0,n,2))  # up(p) <- down(p+1): c_up^dag c_down
S2=None
def spectrum_singlet(Dq,B,C):
    H=build(Dq,B,C)
    Nd=Nop.diagonal(); Sd=Sz2.diagonal()
    idx=np.where((np.abs(Nd-6)<1e-9)&(np.abs(Sd)<1e-9))[0]
    Hs=(H[idx][:,idx]).toarray()
    # S+ S- matrix restricted
    Spm=(Sp.T@Sp)  # S-S+ = (S+)^dag S+ ; S+ sends Sz->Sz+1 ; here use S^- S^+ ~ Sp^T Sp
    Ssub=(Spm[idx][:,idx]).toarray()
    # S^2 = S^- S^+ + Sz(Sz+1), Sz=0 here
    S2m=Ssub
    # null space of S2m
    u,s,vt=np.linalg.svd(S2m)
    null=vt[np.sum(s>1e-8):].T
    Hsing=null.T@Hs@null
    return np.linalg.eigvalsh(Hsing)
