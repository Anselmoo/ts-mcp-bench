python3 - <<'EOF'
import numpy as np
H1,HB,HC,S2=np.load('mats.npy')
for Dq,B in [(3373,1612),(3300,1542)]:
    w,v=np.linalg.eigh(Dq*H1+B*(HB+4.5*HC)); s=np.round(np.diag(v.T@S2@v))
    w-=w[0]; print([(round(w[i]),s[i]) for i in range(0,40)][:40:3])
EOF