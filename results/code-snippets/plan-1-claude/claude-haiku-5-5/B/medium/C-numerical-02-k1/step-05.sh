cd /tmp/tsbench-run-aa74wow9/d7 && sed -i 's/from scipy.special import sph_harm/from scipy.special import sph_harm_y/; s/def Y(l,m): return sph_harm(m,l,PP,TT)/def Y(l,m): return sph_harm_y(l,m,TT,PP)/' d7.py && python3 -c "
from d7 import *
print(ang(0,0,0,0,0), ang(0,2,2,-1,-1), ang(2,2,2,2,2))
"