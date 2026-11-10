cd $TMPDIR && MPLCONFIGDIR=$TMPDIR python3 -c "
exec(open('ts.py').read())
import json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,81); curves={}
def labeled(dq):
    L=levels(max(dq,1e-5)); cnt={}; out=[]
    for e,m,lab in L:
        key=f'{m}{lab}'; cnt[key]=cnt.get(key,0)+1; out.append((e,key+'#'+str(cnt[key])))
    return out
names={'4T1g#1':'4T1g(F)','4T2g#1':'4T2g(F)','4A2g#1':'4A2g(F)','4T1g#2':'4T1g(P)','2Eg#1':'2Eg(G)','2T1g#1':'2T1g(G)','2T2g#1':'2T2g(G)','2A1g#1':'2A1g(G)','2T1g#2':'2T1g(H)','2T2g#2':'2T2g(H)'}
for x in xs:
    out=labeled(x+1.234e-4); g=out[0][0]
    for e,k in out: curves.setdefault(k,[]).append((e-g)/B)
plt.figure(figsize=(7,8))
for k,y in curves.items():
    if len(y)==len(xs) and min(y)<80:
        plt.plot(xs,y,'r-' if k.startswith('4') else 'b-',lw=1)
        if k in names: plt.text(4.02,y[-1],names[k],fontsize=7)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.ylim(0,80);plt.xlim(0,4.5);plt.title('d7 octahedral, B=859, C=3660 cm-1')
plt.savefig('/tmp/tsbench-run-qaym6qt4/diagram.png',dpi=120)
res=[]
for dq in np.arange(0,4.01,0.5):
    out=labeled(dq); g=out[0][0]
    res.append({'dq_over_b':float(dq),'levels':[{'term':names.get(k,k),'e_over_b':round(float((e-g)/B),3)} for e,k in out[:6]]})
print(json.dumps(res))
"; sha256sum /tmp/tsbench-run-qaym6qt4/diagram.png