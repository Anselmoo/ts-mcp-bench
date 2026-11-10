h1=one(hcf(1.0)) 
xs=np.linspace(0,4,41);Y=[]
for r in xs:
    w=np.linalg.eigvalsh(Hee+h1*max(r,1e-3)*B)
    u=[];
    for e in w:
        if not u or e-u[-1]>1e-5*B:u.append(e)
    Y.append((np.array(u[:10])-u[0])/B)
Y=np.array(Y)
plt.figure(figsize=(6,6))
for k in range(Y.shape[1]):plt.plot(xs,Y[:,k])
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d4 Oh, B=814, C=3902');plt.ylim(0,60)
plt.savefig('diagram.png',dpi=120)
