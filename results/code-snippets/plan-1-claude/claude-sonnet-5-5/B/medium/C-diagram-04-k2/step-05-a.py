print([(t,round(e,5)) for t,e in res[0.0][:12]])
fig=plt.figure(figsize=(7,6))
terms=sorted({t for k in res for t,_ in res[k][:6]})
for k in res: pass
xs=sorted(res)
for t in terms:
    pass
# plot lowest 12 levels per point, joined by order
for r in range(10):
    plt.plot(xs,[res[x][r][1] for x in xs],'-o',ms=3)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d6 Tanabe-Sugano, C/B=%.3f'%(C/B))
plt.savefig('diagram.png',dpi=120)
print(hashlib.sha256(open('diagram.png','rb').read()).hexdigest())
import json;json.dump({str(k):[(t,float(e)) for t,e in v[:6]] for k,v in res.items()},open('r.json','w'))
