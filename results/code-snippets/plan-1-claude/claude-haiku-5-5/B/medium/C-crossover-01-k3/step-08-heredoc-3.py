import numpy as np
exec(open('/tmp/tsbench-run-kb_n92kh/d4.py').read().split("for Dq in [0,500")[0])
print("F2,F4",F2,F4)
# check Racah B,C reproduce: 3F-3P-type check via Hee in Ms=2 at Dq=0 (quintet=0)
for Dq in [0]:
    print(lowest_by_spin(Dq) if False else None)
