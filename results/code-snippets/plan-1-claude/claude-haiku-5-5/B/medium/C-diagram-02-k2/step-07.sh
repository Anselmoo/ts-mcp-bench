cat << 'EOF' > dbg2.py
import numpy as np, run
R=run.R; sizes=run.sizes; order=run.order; ct=run.chartab
for k in order:
    print(k, sizes[k], np.round(np.trace(R[k]),4))
for G in ct:
    P=run.proj(G); print(G, np.round(np.trace(P),4), np.allclose(P@P,P))
EOF
python3 dbg2.py