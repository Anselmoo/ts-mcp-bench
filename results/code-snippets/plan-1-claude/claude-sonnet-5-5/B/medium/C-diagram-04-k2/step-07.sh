python3 - <<'E'
s=open('a.py').read()
s=s.replace("float((-1)**a*5*gaunt(2,k,2,-a,a-cc,cc))","float((-1)**a*gaunt(2,k,2,-a,a-cc,cc))*np.sqrt(4*np.pi/(2*k+1))")
s=s.replace("Fk={2:F2/49,4:F4/441}","Fk={2:F2,4:F4}")
open('a.py','w').write(s)
E
MPLCONFIGDIR=<SANDBOX_TMP>/m python3 a.py 2>&1|tail -2; python3 -c "
import json;r=json.load(open('r.json'))
for k,v in r.items():print(k,[(t,round(e,3)) for t,e in v])"