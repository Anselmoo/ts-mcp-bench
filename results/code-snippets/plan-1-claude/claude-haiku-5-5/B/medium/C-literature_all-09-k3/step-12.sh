sed -i 's/groups\[-1\]\[0\]\[0\]/w[groups[-1][0]]/' ligf.py && python3 -c "
from ligf import *
for r in quartet_irreps(740,860,3500): print([round(r[0],1),r[1],r[2]])
"