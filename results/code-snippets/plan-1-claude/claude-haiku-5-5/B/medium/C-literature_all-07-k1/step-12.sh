cd /tmp && python3 - << 'EOF'
import numpy as np
d=np.load('<SANDBOX_TMP>/ops.npz')
Ho,O2,O4,S2=d['Ho'],d['O2'],d['O4'],d['S2']
def H(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    return Dq*Ho+F2*O2+F4*O4
def levels(Dq,B,C):
    w,v=np.linalg.eigh(H(Dq,B,C))
    s=np.einsum('ia,ij,ja->a',v,S2,v)
    E6=w[np.argmin(abs(s-8.75))] if False else None
    sext=w[abs(s-8.75)<1e-6]
    quart=w[abs(s-3.75)<1e-6]
    return sext, quart
sx,q=levels(0,1,0)
print("sextet", sx[:3], len(sx))
sx,q=levels(0,0,0)
print("sextet0", np.round(sx,4)[:3], len(sx))
import collections
for Dq,B,C in [(0,800,3200),(1000,800,3200)]:
    sx,q=levels(Dq,B,C)
    e0=sx.min()
    c=collections.Counter(np.round(q-e0,3))
    print(Dq,B,C, sorted(c.items())[:12])
EOF