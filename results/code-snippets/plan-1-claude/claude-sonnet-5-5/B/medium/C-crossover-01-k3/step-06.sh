cd <SANDBOX_TMP> && sed -i '/^for Dq/,$d' a.py && cat >> a.py <<'E'
for Dq in (0,1000,2000): print(Dq,energies(Dq,4),energies(Dq,2),energies(Dq,0))
E
python3 a.py