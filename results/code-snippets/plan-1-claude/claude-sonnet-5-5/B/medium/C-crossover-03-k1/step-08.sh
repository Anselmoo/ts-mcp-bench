cd <SANDBOX_TMP> && python3 - <<'E'
s=open('a.py').read()
s=s.replace("from sympy.physics.wigner import gaunt","from sympy.physics.wigner import wigner_3j")
import re
s=re.sub(r"return float\(\(-1\)\*\*m1.*\n","return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))\n",s)
open('a.py','w').write(s)
E
grep -n "return float" a.py
cat >> a.py <<'E'
print(c(2,0,0),c(4,0,0))
f=lambda D:gs(D,2)-gs(D,0)
for D in (1000,1500,2000,2500,3000):print(D,f(D))
print(brentq(f,1000,3500))
E
python3 a.py