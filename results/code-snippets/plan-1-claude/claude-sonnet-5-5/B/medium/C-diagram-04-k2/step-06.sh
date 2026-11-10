python3 -c "
import json;r=json.load(open('r.json'))
for k,v in r.items():print(k,[(t,round(e,3)) for t,e in v])"