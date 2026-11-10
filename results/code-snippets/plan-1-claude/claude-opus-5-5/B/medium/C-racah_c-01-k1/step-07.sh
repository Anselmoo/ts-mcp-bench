cd $TMPDIR && python3 -c "
from d3 import *
from scipy.optimize import brentq
C=brentq(lambda c: spec(1417,878,c)[1][0]-18540,3000,5000);print(C, spec(1417,878,C))"