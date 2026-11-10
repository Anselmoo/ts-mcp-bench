cat > final.py << 'EOF'
import numpy as np, main, json
def lowest6(Dq):
    out,err = main.levels_for(Dq)
    allv=[]
    for sec,mult in (('q',4),('d',2)):
        for E,g,Lf,_ in out[sec]:
            allv.append((E, f"{mult}{ {'A1':'A1g','A2':'A2g','E':'Eg','T1':'T1g','T2':'T2g'}[g]}"))
    allv.sort(key=lambda t:t[0])
    E0=allv[0][0]
    return [(lab, (E-E0)) for E,lab in allv[:8]], len(allv)
for x in [1e-4]+[0.5*i for i in range(9)]:
    six,n = lowest6(x)
    print(x, n, [(l, round(e,5)) for l,e in six])
EOF
python3 final.py 2>&1 | grep -v '^{'