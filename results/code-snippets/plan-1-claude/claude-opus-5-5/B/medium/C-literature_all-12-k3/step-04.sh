
cd <SANDBOX_TMP>/tmp.18wMokKLZh
python3 - << 'EOF'
s=open('d7.py').read()
s=s.replace("""                    pb=nd.index(b); sign*=(-1)**pb; nd.pop(pb)
                    pa=nd.index(a); sign*=(-1)**pa; nd.pop(pa)""","""                    pa=nd.index(a); sign*=(-1)**pa; nd.pop(pa)
                    pb=nd.index(b); sign*=(-1)**pb; nd.pop(pb)""")
s=s.replace("c(kk,so[b][0],so[s][0])","c(kk,so[s][0],so[b][0])")
open('d7.py','w').write(s)
EOF
python3 -c "
from d7 import *
for e,l in table(0,800,3200)[:12]: print(round(e),l)
print()
for e,l in table(625,800,3200)[:20]: print(round(e),l)
"
