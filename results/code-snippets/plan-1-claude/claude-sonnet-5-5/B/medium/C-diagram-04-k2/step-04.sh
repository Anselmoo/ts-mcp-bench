python3 - <<'E'
s=open('a.py').read()
s=s.replace("""Sm=np.zeros((N,N))
for det in dets:
    for m in range(5):
        r=app([('c',m),('a',5+m)],det)
        if r: Sm[di[r[1]],di[det]]+=r[0]""","""d1={}
Sm=np.zeros((400,N))
for det in dets:
    for m in range(5):
        r=app([('c',m),('a',5+m)],det)
        if r: Sm[d1.setdefault(r[1],len(d1)),di[det]]+=r[0]""")
open('a.py','w').write(s)
E
MPLCONFIGDIR=/tmp/mpl python3 a.py 2>&1|tail -12