# S^2 operator
S2=np.zeros((N,N))
def spinop():
    M=np.zeros((N,N))
    for dt in dets:
        j=idx[dt]
        # S- S+ : S+ = sum a+_up a_dn ; S2 = S-S+ + Sz(Sz+1)
        # compute S+ S- ... use S2 = S-S+ + Sz^2+Sz
        for p in range(5):
          for q in range(5):
            up_p=2*p; dn_p=2*p+1; up_q=2*q; dn_q=2*q+1
            # S-S+ = sum_{pq} a+_{dn p} a_{up p} a+_{up q} a_{dn q}
            sg,nd=apply(dt,[('c',dn_p),('a',up_p),('c',up_q),('a',dn_q)])
            if sg and nd in idx: M[idx[nd],j]+=sg
    sz=0.5
    return M+(sz*sz+sz)*np.eye(N)
S2=spinop()
def lev2(B,C,Dq):
    F4=C/35;F2=B+5*F4
    H=49*F2*H2+441*F4*H4+Dq*H1
    w,v=np.linalg.eigh(H+0.0*np.eye(N))
    # use H + 1e5*S2 to separate? group by S2 via projecting
    s=np.einsum('ij,ij->j',v.conj(),S2@v).real
    return w-w[0],s
