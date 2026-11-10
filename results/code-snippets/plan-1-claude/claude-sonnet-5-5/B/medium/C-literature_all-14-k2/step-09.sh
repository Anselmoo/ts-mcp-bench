cd <SANDBOX_TMP> && cat >> a.py <<'E'
Cd=np.diag([np.exp(-1j*sum(so[i][0] for i in d)*np.pi/2) for d in dets])
def table(B,C,Dq):
    F4=C/35;F2=B+5*F4
    H=49*F2*H2+441*F4*H4+Dq*H1
    w,v=np.linalg.eigh(H);w=w-w[0]
    out=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<0.5: j+=1
        V=v[:,i:j]
        ch=np.trace(V.conj().T@Cd@V).real
        s=np.trace(V.conj().T@S2@V).real/(j-i)
        out.append((round(w[i]),j-i,round(ch),round(s,2)));i=j
    return out
E
python3 -c "
from a import *
for t in table(900,3200,1000)[:14]: print(t)"