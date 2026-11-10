
def levels_assigned(Dq,B,C):
    Hs,U0,S,C4=build_full(Dq,B,C)
    w=np.real(np.einsum('ia,ij,ja->a',U0,Hs,U0))
    E0=w[np.isclose(S,2.5)].min()
    sel=np.where(np.isclose(S,1.5))[0]
    order=sel[np.argsort(w[sel])]
    groups=[]
    for a in order:
        if groups and abs(w[a]-w[groups[-1][0]])<1e-3*max(1,abs(w[a])): groups[-1].append(a)
        else: groups.append([a])
    info=[]
    C2=C4**2
    for g in groups:
        V=U0[:,g]
        c4=np.real(np.trace(V.conj().T@(C4[:,None]*V)))/4
        c2=np.real(np.trace(V.conj().T@(C2[:,None]*V)))/4
        info.append((w[g[0]]-E0, len(g)//4, round(c4,3), round(c2,3)))
    return info
