cd <SANDBOX_TMP>; python3 -c "
import numpy as np
src=open('a.py').read().split('if __name__')[0]
src=src.replace(\"np.einsum('ac,db->abcd',C[k],C[k])\",\"np.einsum('ac,db->abcd',C[k]*S,C[k])\")
S=np.array([[(-1)**(i-j) for j in range(5)] for i in range(5)])
exec(src)
e=np.linalg.eigvalsh(H(0,900,3500,3));print(np.round(e-e.min()))
open('a3.py','w').write('import numpy as np\nS=np.array([[(-1)**(i-j) for j in range(5)] for i in range(5)])\n'+src)
"