cat > fit0.py << 'EOF'
from oct import levels
import numpy as np, sys
Dq,B,C=map(float,sys.argv[1:4])
L=levels(Dq,B,C)
q=[r for r in L if abs(r[0]-3.75)<0.01]
g=[r for r in L if abs(r[0]-0.75)<0.01]
gs=min(q,key=lambda r:r[1])  # 4T1g(F) ground expected
E0=gs[1]
print('quartets rel:')
for r in sorted(q,key=lambda r:r[1]): print(r[2], round(r[1]-E0,0), r[3])
print('doublets rel:')
for r in sorted(g,key=lambda r:r[1]): print(r[2], round(r[1]-E0,0), r[3])
EOF
python3 fit0.py 810 900 4000 | head -80