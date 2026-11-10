
cd <SANDBOX_TMP>/d7 && python3 -c "
from cross import *
f=lambda d: (lambda L: L[1.5]-L[0.5])(levels(d))
d=brentq(f,1500,2000,xtol=0.5)
print('crossover Dq =',d, 'Dq/B=',d/B, 'C/B=',C/B)
for x in [d-100,d+100]: print(x, levels(x))
"