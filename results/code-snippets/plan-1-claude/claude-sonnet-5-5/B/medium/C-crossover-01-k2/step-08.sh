cd <SANDBOX_TMP>
sed -i 's/^F={2:B+C\/7,4:C\/35}/F={2:49*(B+C\/7),4:441*C\/35}/' a.py
sed -i '/^for D in/,$d' a.py
cat >> a.py <<'E'
for D in (0,1000,2000,3000):print(D,f(D))
print(brentq(f,500,4000,xtol=0.01))
E
python3 a.py