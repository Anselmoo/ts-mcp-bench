
cd /tmp/tsbench-run-uqj8uf3b && time python3 -c "
from fast import levels
import time
t=time.time()
for i in range(100): levels(800,800,3200)
print(time.time()-t)"