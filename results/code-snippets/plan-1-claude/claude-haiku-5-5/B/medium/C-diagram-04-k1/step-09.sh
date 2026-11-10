python3 -c "
from ts import *
import collections
for x in [0.0, 1.0]:
    lv = spectrum(x)
    print('Dq=',x, len(lv))
    seen=collections.OrderedDict()
    for E,t,d in lv:
        seen.setdefault((t,round(E,4)),0); seen[(t,round(E,4))]+=1
    for (t,E),n in list(seen.items())[:14]: print('  ',t,E,'x',n)
" 2>&1 | tail -40