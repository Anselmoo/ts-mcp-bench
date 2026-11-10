
cd /dev/shm && sed -i 's/\*(-1)\*\*m1\*np.sqrt/*np.sqrt/; s/2:{2:.E.}/2:{0:"E"}/' d7.py && python3 fit.py
