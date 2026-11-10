cat > t5.py << 'EOF'
from ts import *
# two electrons both in m=0 orbital, opposite spin: <00|V|00> ; orbital index of m=0 up = 4, down = 5
for k in (0,2,4):
    F={0:0,2:0,4:0}; F[k]=1.0
    print(k, Vint(4,5,4,5,F), Vint(4,5,5,4,F))
EOF
python3 t5.py