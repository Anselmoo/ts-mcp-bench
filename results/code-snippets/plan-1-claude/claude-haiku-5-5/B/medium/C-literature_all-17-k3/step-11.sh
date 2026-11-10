python3 - <<'EOF'
import numpy as np
# coefficient matrices recomputed via quick approach: reuse earlier results by brute recomputation is heavy; instead parametrize check numerically
# Known: for F4=0,F2=1 : triplet 3F=-1.02, 3P=-0.714 ; singlets -0.918,-0.776,-0.571
# For F4=1,F2=0 : triplet 3F=-1.048, 3P=-0.878 ; singlets -0.855,-0.776,-0.571 (centroid not removed)
for F2,F4 in [(49000,0),(0,12.6*1000)]:
    pass
print("ok")
EOF