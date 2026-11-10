print("---")
# S^2 and C4 operators in det basis
def Sminus_plus():
    S2=np.zeros((N,N));
    for d in dets:
        a=di[d]
        Sz=0.5
        S2[a,a]+=Sz*Sz+Sz*0  # Sz^2 + Sz handled below
        # S2 = S-S+ + Sz^2 + Sz ; S-S+ : apply S+ then S-
        S2[a,a]+=Sz
    for d in dets:
        a=di[d]
        for i in range(10):
            if orbs[i][1]==-0.5:
                m=orbs[i][0];up=orbs.index((m,0.5))
                r,s=apply([('c',up),('a',i)],d)
                if r is None:continue
                for j in range(10):
                    if orbs[j][1]==0.5:
                        k=orbs.index((orbs[j][0],-0.5))
                        r2,s2=apply([('c',k),('a',j)],r)
                        if r2 is not None:S2[di[r2],a]+=s*s2
    return S2
S2=Sminus_plus()
C4=np.diag([np.exp(-1j*np.pi/2*sum(orbs[i][0] for i in d)) for d in dets])
for x in (1.45,2.55,3.25):
    w,v=np.linalg.eigh(H(x));w0=w[0]
    i=0;out=[]
    while i<N and len(out)<9:
        j=i
        while j<N and abs(w[j]-w[i])<1e-3:j+=1
        V=v[:,i:j]
        s2=np.trace(V.T@S2@V).real/(j-i);S=(-1+np.sqrt(1+4*s2))/2
        ch=np.trace(V.conj().T@C4@V).real
        out.append((round(w[i]-w0,3),j-i,round(S,2),round(ch,2)));i=j
    print(x,out)
