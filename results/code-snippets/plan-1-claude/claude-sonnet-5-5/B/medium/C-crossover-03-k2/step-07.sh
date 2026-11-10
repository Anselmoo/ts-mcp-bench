cd <SANDBOX_TMP>; sed -i '$d' a.py; sed -i '$d' a.py; cat >> a.py <<'E'
print(brentq(lambda D:gap(D)+1e-3,1300,1500,xtol=0.001))
E
python3 a.py