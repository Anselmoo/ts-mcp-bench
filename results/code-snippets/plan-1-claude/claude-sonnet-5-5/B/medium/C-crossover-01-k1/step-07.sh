sed -i 's/Fk={2:F2,4:F4}/Fk={2:49*F2,4:441*F4}/' a.py
sed -i '/^print(/d;/^import collections/d' a.py
cat >> a.py <<'E'
for D in (1000,1500,2000,2500):print(D,gap(D))
print(brentq(gap,500,3500))
E
python3 a.py