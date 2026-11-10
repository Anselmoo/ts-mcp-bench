cat > t2.py << 'EOF'
from ts import *
for F in [{0:0,2:1,4:0},{0:0,2:0,4:1}]:
    H,st=Hmat(F,0.0,Sz2=3); ev=np.linalg.eigvalsh(H); print(F, np.round(ev-ev.min(),4)[-4:])
EOF
python3 t2.py