
cd <SANDBOX_TMP>/d7 && python3 - << 'EOF'
import re
s=open('d7.py').read()
s=s.replace("from scipy.special import sph_harm","from scipy.special import sph_harm_y\ndef sph_harm(m,l,az,pol): return sph_harm_y(l,m,pol,az)")
open('d7.py','w').write(s)
EOF
time python3 run.py