
cd /dev/shm; PYTHONPATH=/dev/shm python3 -c "
from a import *
w=spec(300,800,3680);print(np.round(w[:12]-w[0],1))
w=spec(0,800,3680);print(np.round(w[:12]-w[0],1))
w=spec(300,0,0);print(np.round(w[:12]-w[0],1))
"
