cat > grid.py << 'EOF'
from analyze import run
import numpy as np
res=[]
for Dq in np.arange(0,4.01,0.5):
    lv=run(Dq)
    E0=lv[0][0]
    six=[(round(e-E0,4),l) for e,l in lv[:6]]
    res.append((round(Dq,2),six))
    print(f"Dq/B={Dq:.1f}: "+", ".join(f"{l} {e:.4f}" for e,l in six))
    print("   full lowest 8:", ", ".join(f"{l} {e-E0:.3f}" for e,l in lv[:8]))
EOF
python3 grid.py 2>&1 | grep -v -E "group order|hom err|Counter"