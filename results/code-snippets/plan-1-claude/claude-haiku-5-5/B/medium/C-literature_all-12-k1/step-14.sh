cat > grid.py << 'EOF'
import numpy as np
from fit2 import spectra
best=[]
for Dq in np.arange(550,720,10):
    for B in np.arange(500,1100,20):
        q,_=spectra(Dq,B,0)
        q=q-q[0]
        m=np.array([q[3],q[6],q[7]])
        r=m-np.array([6150,12400,16850])
        best.append((np.sum(r**2)**0.5,Dq,B,np.round(r,0)))
best.sort(key=lambda x:x[0])
for b in best[:6]: print(b)
EOF
python3 grid.py 2>&1 | grep -v "cf eig"