cd ~ 2>/dev/null; cd /tmp/tsbench-run-kb_n92kh && sed -i 's/^F4=C\*7\/5; F2=49\*B+5\*F4/F4=441*C\/35; F2=(441*B+5*F4)\/9/' d4.py && python3 - << 'EOF'
import re
src=open('d4.py').read()
src=src.split("for Dq in [0,500")[0]+src.split("print(Dq, lowest_by_spin(Dq))\n")[1] if False else src
open('d4b.py','w').write(src)
EOF
grep -n "F4=" d4.py; cat >> d4.py << 'EOF'
EOF
python3 - << 'EOF'
import numpy as np
exec(open('/tmp/tsbench-run-kb_n92kh/d4.py').read().split("for Dq in [0,500")[0])
print("F2,F4",F2,F4)
# check Racah B,C reproduce: 3F-3P-type check via Hee in Ms=2 at Dq=0 (quintet=0)
for Dq in [0]:
    print(lowest_by_spin(Dq) if False else None)
EOF