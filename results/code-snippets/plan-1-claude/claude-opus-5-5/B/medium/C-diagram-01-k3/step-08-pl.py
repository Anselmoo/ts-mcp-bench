import pickle,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
B=828.;res=pickle.load(open('res.pkl','rb'))
dqs=sorted(res);tr={}
for dq in dqs:
    r=res[dq];e0=min(x[0] for x in r);cnt={}
    for e,m,ir in r:
        k=f'{m}{ir}';i=cnt.get(k,0);cnt[k]=i+1
        tr.setdefault((k,i),[]).append((e-e0)/B)
plt.figure(figsize=(7,8))
for (k,i),y in tr.items():
    plt.plot(dqs,y,'-' if k[0]=='4' else '--',lw=1)
    plt.text(dqs[-1]+0.03,y[-1],f'$^{k[0]}{k[1]}_{{{k[2:]}g}}$' if len(k)>2 else f'$^{k[0]}{k[1]}_g$',fontsize=7)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.ylim(0,80);plt.xlim(0,4.4)
plt.title('Tanabe–Sugano d$^3$ O$_h$, B=828, C=3390 cm$^{-1}$')
plt.savefig('/tmp/tsbench-run-9h9z_klt/diagram.png',dpi=120)
