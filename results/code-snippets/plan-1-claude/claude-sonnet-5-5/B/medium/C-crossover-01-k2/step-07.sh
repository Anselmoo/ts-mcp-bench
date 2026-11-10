cd <SANDBOX_TMP>
sed -i '/^for D in/,$d' a.py
cat >> a.py <<'E'
for D in (0,200,400,600,800):print(D,f(D))
print(brentq(f,0,1000,xtol=0.01))
E
python3 a.py