cd ./ts && cat > dbg2.py << 'EOF'
import numpy as np
import ts
H=ts.build_H(0.0)
s2vals,s2vecs=np.linalg.eigh((ts.S2+ts.S2.T)/2)
W=s2vecs[:,np.abs(s2vals-8.75)<1e-6]
Hs=W.conj().T@H@W
ev,X=np.linalg.eigh((Hs+Hs.conj().T)/2)
print(np.round(ev,4))
V=W@X
chis=[np.trace(V.conj().T@Om@V) for Om in ts.Oms]
print(np.round(chis,4))
print(ts.decompose(chis))
print("Rep chars check (6 sextet):", [np.round(np.trace(W.conj().T@Om@W),3) for Om in ts.Oms])
EOF
timeout 900 python3 dbg2.py 2>&1 | grep -v -i matplotlib