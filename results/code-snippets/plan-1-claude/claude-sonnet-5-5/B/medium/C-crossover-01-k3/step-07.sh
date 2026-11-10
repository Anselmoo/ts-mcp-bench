cd <SANDBOX_TMP> && sed -i 's/return np.linalg.eigvalsh(Hm)\[0\]/return np.linalg.eigvalsh(Hm)/' a.py
sed -i '/^for Dq/,$d' a.py
cat >> a.py <<'E'
def trip(Dq):
    e5=energies(Dq,4); e3=energies(Dq,2)
    rem=list(e3)
    for x in e5:
        i=min(range(len(rem)),key=lambda j:abs(rem[j]-x)); rem.pop(i)
    return min(rem), e5[0]
def g(Dq):
    t,q=trip(Dq); return q-t
for Dq in (0,1000,2000,3000): print(Dq,g(Dq))
print(brentq(g,500,4000,xtol=1e-6))
E
python3 a.py