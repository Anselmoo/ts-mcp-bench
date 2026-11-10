cd <SANDBOX_TMP> && python3 - <<'E'
from a import *
def f(p):
    u=levels(*p); return [u[1][0]-19180,u[2][0]-22130,u[3][0]-23370]
for g in [(800,800,3000),(700,700,3500)]:
    r=fsolve(f,g,full_output=True); print(r[0],f(r[0]))
E