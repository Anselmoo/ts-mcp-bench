M=np.array([sum(so[o][0] for o in d) for d in dets])
R=np.exp(-1j*np.pi/2*M)
for D in (1.45,2.45,3.0):
    e,v=np.linalg.eigh(H2+D*B*Hc); e-=e[0]
    i=0;out=[]
    while i<120 and len(out)<7:
        j=i
        while j<120 and e[j]-e[i]<1e-3*B: j+=1
        V=v[:,i:j]; tr=np.trace(V.conj().T@(R[:,None]*V))
        out.append((round(e[i]/B,2),j-i,np.round(tr,2))); i=j
    print(D,out)
