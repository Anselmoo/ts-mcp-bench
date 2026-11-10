import re
src=open('ligf.py').read()
src=src.replace("    Hs=H[np.ix_(idx,idx)]\n    w,U=np.linalg.eigh(Hs)\n    ss=np.real(np.einsum('ia,ij,ja->a',U,S2s,U))\n    return w,ss",
"    Hs=H[np.ix_(idx,idx)]\n    w0,U0=np.linalg.eigh(Hs+1000.0*S2s)\n    ss=np.real(np.einsum('ia,ij,ja->a',U0,S2s,U0))\n    w=np.real(np.einsum('ia,ij,ja->a',U0,Hs,U0))\n    return w,ss")
open('ligf.py','w').write(src)
