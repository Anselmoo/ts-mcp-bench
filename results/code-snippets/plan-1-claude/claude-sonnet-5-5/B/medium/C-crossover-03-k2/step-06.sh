cd <SANDBOX_TMP>; sed -i '$d' a.py; sed -i '$d' a.py; cat >> a.py <<'E'
for D in (500,800,900,1000,1100,1200,1300): print(D,gap(D))
print(brentq(gap,1000,1500,xtol=0.01))
E
python3 a.py