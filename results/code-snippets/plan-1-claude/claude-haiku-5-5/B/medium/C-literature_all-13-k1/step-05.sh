cd /tmp && python3 - << 'EOF'
from sympy.physics.wigner import gaunt
from sympy import N
from math import pi
# check gaunt values vs known: <Y00 Y00 Y00> = 1/sqrt(4pi)
print(N(gaunt(0,0,0,0,0,0)), 1/(4*pi)**0.5)
# check Y22 Y2-2 Y20 etc
print(N(gaunt(2,2,2,0,0,0)))
EOF