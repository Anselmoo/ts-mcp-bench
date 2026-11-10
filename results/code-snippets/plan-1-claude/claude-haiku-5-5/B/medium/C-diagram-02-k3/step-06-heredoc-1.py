import re
src = open('ts.py').read()
src = src.replace("""        Bs = blk[:, subsets]              # (N,4,4)  columns S
        Bs = np.transpose(Bs, (0,1,2))""", """        Bs = np.transpose(blk[:, subsets], (1,0,2))   # (N,4,4)""")
src = src.replace("""        r = None
        if (2*a+1) in s and (2*a) not in s:
            r = annih(2*a+1, s); r = create(2*a, r[1]) and (r[0]*create(2*a, r[1])[0], create(2*a, r[1])[1])
            Sp[index[r[1]], n] += r[0]""", """        r = annih(2*a+1, s)           # S+ = sum c_up^dag c_dn
        if r is None: continue
        r2 = create(2*a, r[1])
        if r2 is None: continue
        Sp[index[r2[1]], n] += r[0]*r2[0]""")
open('ts.py','w').write(src)
