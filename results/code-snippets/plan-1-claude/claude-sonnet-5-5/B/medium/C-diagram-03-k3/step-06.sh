python3 - <<'E'
s=open('t.py').read()
s=s.replace("def opmat(R):","""def sg(d):
    return (-1)**sum(1 for p in d if p%2==1 for q in d if q%2==0 and q>p)
def opmat(R):""")
s=s.replace("M[idx[new],j]=np.linalg.det","M[idx[new],j]=sg(new)*sg(d)*np.linalg.det")
open('t.py','w').write(s)
E
python3 t.py