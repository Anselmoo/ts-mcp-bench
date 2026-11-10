cat > c.py <<'E'
from t import *
H=build(0);w=np.linalg.eigvalsh(H);print(np.round((w[:45]-w[0])/B,3))
print(abs(H-H.T).max(), abs(H@S2-S2@H).max())
E
python3 c.py