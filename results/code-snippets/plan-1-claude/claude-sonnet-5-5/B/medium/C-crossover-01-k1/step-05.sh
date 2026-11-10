cat >> a.py <<'E'
print(A[(2,2,2)],A[(4,2,2)],A[(2,0,0)],A[(4,0,0)])
E
python3 a.py | tail -1