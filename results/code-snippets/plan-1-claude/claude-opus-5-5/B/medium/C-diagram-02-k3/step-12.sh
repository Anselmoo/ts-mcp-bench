cat > plot.py <<'EOF'
import json,zlib,struct,hashlib
d=json.load(open('all.json'))
xs=sorted(d,key=float)
# relabel duplicates
def rel(lst):
    seen={};out=[]
    for l,e in lst: out.append(l)
    return out
W,H=900,700; img=[[255]*W*3 for _ in range(H)]
def px(x,y,c):
    if 0<=x<W and 0<=y<H: img[y][3*x:3*x+3]=c
def line(x0,y0,x1,y1,c):
    n=max(abs(x1-x0),abs(y1-y0),1)
    for i in range(n+1):
        x=round(x0+(x1-x0)*i/n); y=round(y0+(y1-y0)*i/n)
        for dx in (0,1):
            px(x+dx,y,c)
X=lambda dq:60+dq/4.0*(W-90)
Y=lambda e:H-50-e/80*(H-80)
line(60,H-50,W-30,H-50,(0,0,0)); line(60,H-50,60,30,(0,0,0))
for t in range(9): line(round(X(t*0.5)),H-50,round(X(t*0.5)),H-44,(0,0,0))
for t in range(0,81,10): line(54,round(Y(t)),60,round(Y(t)),(0,0,0))
cols={5:(200,0,0),3:(0,0,200),1:(0,140,0)}
nlev=len(d[xs[0]])
for k in range(nlev):
    for a,b in zip(xs,xs[1:]):
        la,ea=d[a][k]; lb,eb=d[b][k]
        if ea>80 and eb>80: continue
        # sorted index tracking (adequate for visualization)
        line(round(X(float(a))),round(Y(ea)),round(X(float(b))),round(Y(eb)),cols[int(la[0])])
raw=b''.join(b'\x00'+bytes(r) for r in img)
def chunk(t,data): return struct.pack('>I',len(data))+t+data+struct.pack('>I',zlib.crc32(t+data)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
open('diagram.png','wb').write(png)
print(hashlib.sha256(png).hexdigest())
EOF
python3 plot.py; realpath diagram.png