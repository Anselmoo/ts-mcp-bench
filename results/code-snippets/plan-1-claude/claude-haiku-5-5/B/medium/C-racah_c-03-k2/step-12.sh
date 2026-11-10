cat > chk.py << 'EOF'
import numpy as np
exec(open('run_d3.py').read().split('H2=two_body')[0])
print("V2[m=0,m=0,m=0,m=0] =", V2[2,2,2,2].real, " expect 4/49 *F2 ->", 4/49)
print("V4[0000] =", V4[2,2,2,2].real, " expect 18/441 F4 ->", 18/441)
print("V0 check: trace over H would be zero")
EOF
python3 chk.py