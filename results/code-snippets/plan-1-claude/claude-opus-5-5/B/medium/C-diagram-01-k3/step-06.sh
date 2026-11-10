cd $TMPDIR && cat > an.py <<'EOF'
import pickle,numpy as np
B=828.
res=pickle.load(open('res.pkl','rb'))
# free ion terms at dq=0
r0=res[0.0]; e0=min(x[0] for x in r0)
for x in r0: print(round((x[0]-e0)/B,3),x[1],x[2])
EOF
python3 an.py