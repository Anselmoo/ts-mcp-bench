python3 - <<'E'
import pickle,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=pickle.load(open('<SANDBOX_TMP>/r.pkl','rb'))
plt.figure()
for k in range(6):
    plt.plot(list(r),[r[d][k][0] for d in r],'o-')
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d5 Oh, 6 lowest levels (points)')
plt.savefig('diagram.png',dpi=100)
E
sha256sum $PWD/diagram.png; pwd