python3 -c "
import json
for r in json.load(open('res.json')): print(r['dq_over_b'],[(l['term'],l['e_over_b']) for l in r['levels']])"; realpath diagram.png