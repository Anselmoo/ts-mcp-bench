cat > fitq.py << 'EOF'
import numpy as np
from fit2 import spectra
from scipy.optimize import least_squares
def mq(p):
    q,_=spectra(p[0],p[1],0)
    q=q-q[0]
    return np.array([q[3],q[6],q[7]])
obs=np.array([6150,12400,16850.])
for s in [(615,800),(650,900),(700,700),(600,1000)]:
    sol=least_squares(lambda p: (mq(p)-obs)/10., s, bounds=([300,300],[1200,1500]))
    print(np.round(sol.x,1), np.round(mq(sol.x)-obs,1), sol.cost)
EOF
python3 fitq.py 2>&1 | grep -v "cf eig"