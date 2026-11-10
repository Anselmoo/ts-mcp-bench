cd /dev/shm && python3 -c "
from ts import *
from fractions import Fraction
V=Vspat({2:1.0,4:0.0})
vals=set()
for a,b,c,d in itertools.product(range(5),repeat=4):
    if abs(V[a,b,c,d])>1e-12: vals.add(round(V[a,b,c,d],8))
print(sorted(vals))
print([Fraction(x).limit_denominator(1000) for x in sorted(vals)])
"