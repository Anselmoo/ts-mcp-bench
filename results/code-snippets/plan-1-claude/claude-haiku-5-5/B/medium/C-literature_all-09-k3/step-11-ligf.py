
def build_full(Dq,B,C):
    F=(0.0,49*B+7*C,63*C/5.0)
    Peg=np.zeros((5,5)); Peg[2,2]=1
    v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2)
    Peg+=np.outer(v,v)
    Vmat=-4*Dq*np.eye(5)+10*Dq*Peg
    H=np.zeros((dim,dim))
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            if s1==s2 and abs(Vmat[m1+2,m2+2])>1e-14:
                H+=Vmat[m1+2,m2+2]*cre[i]@ann[j]
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            for k,(m3,s3) in enumerate(orbs):
                if s1!=s3: continue
                for l,(m4,s4) in enumerate(orbs):
                    if s2!=s4 or i==j or k==l: continue
                    val=Vsp(m1,m2,m3,m4,F)
                    if abs(val)<1e-12: continue
                    H+=0.5*val*(cre[i]@cre[j]@ann[l]@ann[k])
    Hs=H[np.ix_(idx,idx)]
    w0,U0=np.linalg.eigh(Hs+1000.0*S2s)
    ss=np.real(np.einsum('ia,ij,ja->a',U0,S2s,U0))
    S=np.round((-1+np.sqrt(1+4*ss))/2*2)/2
    Mz=np.array([sum(orbs[i][0] for i in range(n) if (st>>i)&1) for st in idx],dtype=float)
    C4=np.exp(-1j*np.pi/2*Mz)  # diagonal C4z rotation in Fock space (occupations of m)
    return Hs,U0,S,C4
def quartet_irreps(Dq,B,C):
    Hs,U0,S,C4=build_full(Dq,B,C)
    w=np.real(np.einsum('ia,ij,ja->a',U0,Hs,U0))
    E0=w[np.isclose(S,2.5)].min()
    out=[]
    sel=np.where(np.isclose(S,1.5))[0]
    # group eigenvalues by clustering
    order=sel[np.argsort(w[sel])]
    groups=[]
    for a in order:
        if groups and abs(w[a]-groups[-1][0][0])<1e-3*max(1,abs(w[a])):
            groups[-1].append(a)
        else: groups.append([a])
    for g in groups:
        V=U0[:,g]
        chi=np.real(np.trace(V.conj().T@(C4[:,None]*V)))/4.0
        out.append((w[g[0]]-E0, len(g)//4, round(chi,3)))
    return out
