cd /tmp/tsbench-run-l39pr0fd; python3 - <<'E'
import re
s=open('run2.py').read()
a=s.index("        key=(int(round(c4))")
b=s.index("        res.append")
new='''        R2s=R4@R4
        c2s=np.trace(P.conj().T@R2s@P).real/m
        tgt=(deg//m,round(c2s),round(c4),round(c2))
        assert deg%m==0
        best=None
        for cnt in itertools.product(range(4),repeat=5):
            if tuple(sum(cnt[k]*CH[k][t] for k in range(5)) for t in range(4))==tgt:
                if best is None or sum(cnt)<sum(best): best=cnt
        assert best is not None,(tgt)
        for k in range(5):
            for _ in range(best[k]): res.append((e,f"{m}{NM[k]}g",CH[k][0]))
        i=j; continue
'''
s=s[:a]+new+s[b:]
s=s.replace("irr={","CH=[(1,1,1,1),(1,1,-1,-1),(2,2,0,0),(3,-1,1,-1),(3,-1,-1,1)]\nNM=['A1','A2','E','T1','T2']\nirr={")
s=s.replace("res.append((e,f\"{m}{irr[key]}g\",deg//m)); i=j","pass")
open('run2.py','w').write(s)
E
python3 run2.py 2>&1 | grep -v matplotlib