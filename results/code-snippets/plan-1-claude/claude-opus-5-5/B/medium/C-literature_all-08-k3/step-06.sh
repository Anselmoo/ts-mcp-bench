
cd <SANDBOX_TMP>/tmp.08ajEaEhMw && cat >> d5.py << 'EOF'
from scipy.optimize import minimize
f=lambda x: sum(r*r for r in res2(x))
s=minimize(f,[600,780,3100],method='Nelder-Mead',options={'xatol':0.01,'fatol':1e-4,'maxiter':4000});print(s.x,res2(s.x),levels(*s.x)[:6])
EOF
python3 d5.py 2>&1 | tail -1