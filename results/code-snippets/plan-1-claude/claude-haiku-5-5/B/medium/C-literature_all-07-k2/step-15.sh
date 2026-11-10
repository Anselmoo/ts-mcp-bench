
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > full.py
from fit import levels
import sys
Dq,B,C=map(float,sys.argv[1:4])
Esx,cl=levels(Dq,B,C)
for e,d in cl: print(round(e,1),d)
EOF
timeout 900 python3 full.py 0 800 3200; echo; timeout 900 python3 full.py 800 800 3200