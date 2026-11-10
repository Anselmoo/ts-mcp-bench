python3 - << 'EOF'
import re
src=open('ligf.py').read()
src=src.replace("    Hs=H[np.ix_(idx,idx)]\n    w,U=np.linalg.eigh(Hs)\n    ss=np.real(np.einsum('ia,ij,ja->a',U,S2s,U))\n    return w,ss",
"    Hs=H[np.ix_(idx,idx)]\n    w0,U0=np.linalg.eigh(Hs+1000.0*S2s)\n    ss=np.real(np.einsum('ia,ij,ja->a',U0,S2s,U0))\n    w=np.real(np.einsum('ia,ij,ja->a',U0,Hs,U0))\n    return w,ss")
open('ligf.py','w').write(src)
EOF
python3 -c "
from ligf import *
import numpy as np
w,ss=build(0,1.0,0.0)
S=np.round((-1+np.sqrt(1+4*ss))/2*2)/2
for s in sorted(set(S)):
    sel=np.isclose(S,s)
    vals=np.round(w[sel]-w.min(),3)
    u,c=np.unique(vals,return_counts=True)
    print('S=',s,'n=',sel.sum(),list(zip(u,c)))
"