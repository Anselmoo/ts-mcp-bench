cat >> calib.py << 'EOF'

# doublet block: average energy per L subspace (relative to quartet 4F)
Ld = block(L2.real,d_idx)
w,V = np.linalg.eigh(Ld)
F4ref = {}
E4F2 = -0.877551; E4F4 = -0.734694
for H,lab in ((H2,'F2'),(H4,'F4')):
    pass
# restrict doublet space to orthogonal complement of quartet lowering states
Sm = np.zeros((ts.N,ts.N))
for j,bj in enumerate(ts.basis):
    for m in range(5):
        p_dn = 2*m+1; p_up = 2*m
        s1,b1 = ts.ann(p_up,bj)
        if s1==0: continue
        s2,b2 = ts.cre(p_dn,b1)
        if s2==0: continue
        Sm[ts.idx[b2],j] += s1*s2
Qv = Sm[np.ix_(d_idx,q_idx)]
U_,s_,_ = np.linalg.svd(Qv)
Qbasis = U_[:,:len(q_idx)]  # columns span quartet M=1/2 (rank 10)
Pn = np.eye(len(d_idx)) - Qbasis@Qbasis.conj().T
u,sv,vh = np.linalg.svd(Pn)
Pd = u[:,:40]
for H,lab in ((H2,'F2'),(H4,'F4')):
    Hd = Pd.conj().T @ block(H,d_idx) @ Pd
    Ld2 = Pd.conj().T @ Ld @ Pd
    Hd = Hd.real; Ld2=Ld2.real
    # simultaneous: diagonalize L2 in doublet space then take traces per L
    wl,Vl = np.linalg.eigh(Ld2)
    out=[]
    for L2v in sorted(set(np.round(wl,6))):
        sel = np.abs(wl-L2v)<1e-6
        Vs = Vl[:,sel]
        Hs = Vs.T@Hd@Vs
        out.append((L2v, sel.sum(), np.trace(Hs)/sel.sum()))
    print(lab, [(round(a,3),b,round(c,6)) for a,b,c in out])
EOF
python3 calib.py