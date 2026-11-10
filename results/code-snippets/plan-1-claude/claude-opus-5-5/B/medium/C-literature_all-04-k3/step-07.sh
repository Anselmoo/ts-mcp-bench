cd $TMPDIR && cat >> d3.py << 'EOF'
EOF
sed -i 's/^sol=fsolve.*$//; s/^print(\[(round(a,1),b) for a,b in levels(\*sol).*$//' d3.py
cat >> d3.py << 'EOF'
from scipy.optimize import brentq
B=282240000/462000
def g(C):
    e=np.linalg.eigvalsh(1750*H1+(49*B+7*C)*G2+12.6*C*G4); e-=e[0]
    return e[4]-14300
C=brentq(g,2000,5000); print(B,C,C/B)
print([(round(a,1),b) for a,b in levels(1750,B,C)[:8]])
EOF
python3 d3.py