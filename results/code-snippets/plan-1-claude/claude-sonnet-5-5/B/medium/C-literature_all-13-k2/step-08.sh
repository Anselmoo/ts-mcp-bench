cd <SANDBOX_TMP>; python3 -c "
import a
from a import *
import numpy as np
# redefine H with sign
src=open('a.py').read().replace(\"np.einsum('ac,db->abcd',C[k],C[k])\",\"np.einsum('ac,bd->abcd',C[k],C[k])\")
exec(src.split('if __name__')[0])
e=np.linalg.eigvalsh(H(0,900,3500,3));print(np.round(e-e.min()))
open('a2.py','w').write(src)
"