cat > ref.py << 'EOF'
import numpy as np
from scan import levels
obs=np.array([29360,29620,31640.])
for r in [4.40,4.45,4.50,4.55,4.60]:
    L=levels(r,1.0); ex=np.array([v for v,m in L[1:4]])
    B=np.dot(ex,obs)/np.dot(ex,ex)
    res=B*ex-obs
    print(r, round(B,2), round(r*B,1), np.round(res,1))
EOF
python3 ref.py 2>/dev/null | grep -v norm