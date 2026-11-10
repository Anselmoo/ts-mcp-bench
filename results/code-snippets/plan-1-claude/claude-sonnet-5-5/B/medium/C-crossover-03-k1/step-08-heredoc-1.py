s=open('a.py').read()
s=s.replace("from sympy.physics.wigner import gaunt","from sympy.physics.wigner import wigner_3j")
import re
s=re.sub(r"return float\(\(-1\)\*\*m1.*\n","return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))\n",s)
open('a.py','w').write(s)
