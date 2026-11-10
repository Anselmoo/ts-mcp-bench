cat > grid.py << 'EOF'
import numpy as np
from fit2 import quartet_rel, triplets, spectrum
obs=np.array([6150,12400,16850])
best=[]
for Dq in range(500,901,50):
  for B in range(500,1301,100):
    for C in range(2500,5001,500):
        qr=quartet_rel((Dq,B,C))
        r=np.sum((qr[1:4]-obs)**2)
        best.append((np.sqrt(r/3),Dq,B,C,np.round(qr,0)))
best.sort(key=lambda t:t[0])
for b in best[:8]: print(b)
EOF
python3 grid.py