cd /dev/shm/d4 && python3 - << 'EOF'
import re
s=open('d4.py').read()
s=s.replace("from scipy.special import sph_harm","from scipy.special import sph_harm_y")
s=s.replace("def Y(l,m,th,phi): return sph_harm(m,l,phi,th)","def Y(l,m,th,phi): return sph_harm_y(l,m,th,phi)")
open('d4.py','w').write(s)
EOF
time python3 run.py