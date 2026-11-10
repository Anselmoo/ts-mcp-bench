cd <SANDBOX_TMP>/w && cat > dbl.py << 'EOF'
from ts import *
Dq,B = np.load('sol.npy')
def analyze(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    H = build_H(Dq,B,C); H=0.5*(H+H.conj().T).real
    # Lz phase for C4 rotation (pi/2) : exp(-i*pi/2*sum m)
    Lz = np.array([sum(ms[x//2] for x in d) for d in dets])
    R = np.diag(np.exp(-1j*np.pi/2*Lz))
    # restrict to S=1/2 subspace via S2 projection: diagonalize H + 100*S2 (shift S2 eigen)
    M = H + 1e4*S2
    w,v = np.linalg.eigh(M)
    out=[]
    # group by energy
    i=0
    while i < len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-4*max(1,abs(w[i])): j+=1
        vs = v[:,i:j+1]
        s2 = np.real(np.trace(vs.conj().T@S2@vs))/(j-i+1)
        if abs(s2-0.75)<1e-6:
            tr = np.trace(vs.conj().T@R@vs)
            out.append((w[i]-1e4*0.75 - 0, j-i+1, np.round(tr,3)))
        i=j+1
    return out
if __name__=="__main__":
    import sys
    Dq_,B_=Dq,B
    q,_=levels(Dq_,B_,4*B_)
    g0=q[0]
    res=analyze(Dq_,B_,4*B_)
    # energy relative to ground: need ground eigenvalue; recompute with same method
    for e,dg,tr in res:
        print(dg, tr)
EOF
python3 dbl.py 2>&1 | tail -20