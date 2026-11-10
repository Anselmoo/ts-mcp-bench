python3 -c "
from ligf import *
import numpy as np
Hs,U0,S,C4=build_full(740,860,3500)
w=np.real(np.einsum('ia,ij,ja->a',U0,Hs,U0))
sel=np.where(np.isclose(S,1.5))[0]
ww=np.sort(w[sel]); print(len(ww))
print(np.round(ww-ww.min(),2)[::4])
print(np.round(np.diff(ww),3)[:200])
" | head -30