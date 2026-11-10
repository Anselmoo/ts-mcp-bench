sed -i '/^for D in/,$d' a.py; cat >> a.py <<'E'
print(ham(4,0)[:6]);print(ham(2,0)[:8])
E
python3 a.py