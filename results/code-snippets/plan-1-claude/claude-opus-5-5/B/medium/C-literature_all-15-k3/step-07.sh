
cd <SANDBOX_TMP> && cat >> fit2me.py << 'EOF'
from scipy.optimize import fsolve
for keys in [[('4T2',1),('4T1',2),('2T1',2)],[('4A2',1),('4T1',2),('2T1',2)],[('4T2',1),('4A2',1),('2T1',2)]]:
    f=lambda p:[pick(*p)[k]-obs[k] for k in keys]
    x=fsolve(f,[850,850,3500]); print(keys,x,res(x))
EOF
python fit2me.py | tail -3