
cd <SANDBOX_TMP>/tmp.dJiUhyh28T && cat << 'EOF' > chk2.py
exec(open('d7.py').read().split('print("Dq only')[0])
def free(F2,F4):
    V=(F2*A2+F4*A4).reshape(25,25)
    Hs=Bm.conj().T@V@Bm
    return np.sort(np.linalg.eigvalsh((Hs+Hs.conj().T)/2)).real
print("F2 only", free(1,0).round(5))
print("F4 only", free(0,1).round(5))
EOF
python3 chk2.py
