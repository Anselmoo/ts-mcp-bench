cd /dev/shm; python3 - <<'E'
E
cat >> /dev/shm/t.py <<'E'
def lev(Dq,B,Cc):
    H=build(Dq,B,Cc);H=(H+H.T)/2
    w=np.linalg.eigvalsh(H);w=w-w[0];u=[]
    for x in w:
        if not u or abs(x-u[-1][-1])>20:u.append([x,1,x])
        else:u[-1][1]+=1;u[-1][2]=x
    return [(x,n) for x,n,_ in u]
def quart(Dq,B):
    u=lev(Dq,B,3000)
    e12=[x for x,n in u if n==12];e4=[x for x,n in u if n==4 and abs(x-12400)<3500]
    return np.array([e12[1],e4[0],e12[2]])
obs=np.array([6150,12400,16850])
best=[]
for Dq in np.arange(560,761,20):
  for B in np.arange(650,951,25):
    try:
        r=quart(Dq,B)-obs
        best.append((np.sum(r**2),Dq,B,r))
    except Exception as e: pass
best.sort(key=lambda x:x[0])
for b in best[:5]:print(b)
E
python3 /dev/shm/t.py | tail -6