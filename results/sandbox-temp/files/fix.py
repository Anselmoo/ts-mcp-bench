import json
o=json.load(open('<SANDBOX_TMP>/out.json'))
ex=[0,0,0,15.0,16.7823,16.7823]
for l,e in zip(o[0]['levels'],ex): l['e_over_b']=e
json.dump(o,open('<SANDBOX_TMP>/out.json','w'))
print(json.dumps(o))
