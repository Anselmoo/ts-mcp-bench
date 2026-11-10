cd /dev/shm/d5 && python3 -c "
import numpy as np
exec(open('d5.py').read().split('G = list')[0])
print(len(G))
" 2>&1 | tail -3; sed -n 40,46p /dev/shm/d5/d5.py