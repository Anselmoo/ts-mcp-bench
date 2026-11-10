def lv(Dq,B,Cc):
    H=build(Dq,B,Cc)[np.ix_(sel,sel)];s=SS[np.ix_(sel,sel)]
    w,v=np.linalg.eigh(H);ss=np.einsum('ij,ik,kj->j',v,s,v)
    gs=w[np.argmin(abs(ss-8.75))];q=np.sort(w[abs(ss-3.75)<0.1]-gs)
    out=[q[0]]
    for e in q[1:]:
        if e-out[-1]>1e-3: out.append(e)
    return out
def res2(x):
    q=lv(*x);return [q[0]-19240,q[1]-21890,q[2]-23000]
r=least_squares(res2,[800,700,3200],diff_step=1e-4);print(r.x,lv(*r.x)[:5],res2(r.x))
