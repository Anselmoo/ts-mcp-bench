exec(open('run.py').read().split('o=spectrum(1,0,0)')[0])
# C4 about z many-body operator: exp(-i pi/2 Lz), Lz = sum m n_{m,s}
Lz=sum(ms[o]*(C[so(o,0)]@Ann[so(o,0)]+C[so(o,1)]@Ann[so(o,1)]) for o in range(5))
Lz=Lz[np.ix_(idx,idx)]
C4=np.diag(np.exp(-1j*np.pi/2*np.diag(Lz).real))  # Lz diagonal in Fock basis
assert np.allclose(Lz,np.diag(np.diag(Lz)))
def levels_sym(Dq,B,C_):
    H=build_H(Dq,B,C_)[np.ix_(idx,idx)]
    res={}
    for S in [1.5,0.5]:
        sel=np.abs(ws-S*(S+1))<1e-6
        U=Us[:,sel]
        Hsub=U.T@H@U; Hsub=(Hsub+Hsub.T)/2
        w,V=np.linalg.eigh(Hsub)
        W=U@V  # full-space eigenvectors
        groups=[]
        i=0
        while i<len(w):
            j=i
            while j+1<len(w) and abs(w[j+1]-w[i])<1e-6: j+=1
            Vg=W[:,i:j+1]
            tr=np.trace(Vg.conj().T@C4@Vg)
            groups.append((w[i],j-i+1,np.round(tr.real,3)))
            i=j+1
        res[S]=groups
    return res
if __name__=="__main__":
    for p in [(1,0,0),(0.7,1,4)]:
        r=levels_sym(*p)
        for S in r: print(p,S,[(round(a,3),b,c) for a,b,c in r[S]])
