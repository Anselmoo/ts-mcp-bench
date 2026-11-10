sed -i 's/A\[k\]\[m2+2,m4+2\]/A[k][m4+2,m2+2]/' t.py; python3 -c "
from t import *
print(np.round(A[2],4));print(np.round(A[4],4))"