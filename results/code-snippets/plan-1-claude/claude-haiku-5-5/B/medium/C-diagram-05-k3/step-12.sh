cd <SANDBOX_TMP>/ts && sed -i 's/key=lambda t:(round(t\[0\],6), d_eps\[t\[1\]\])/key=lambda t:(round(t[0],4), d_eps[t[1]])/' final.py && python3 final.py 2>&1 | grep -E "Dq=0 first|Dq/B=0.0"; python3 -c "
exec(open('run3.py').read().split('if __name__')[0].replace('exec(open(\'run.py\').read().split(\'# Dq=0 analysis\')[0])','from run import *'))
" >/dev/null 2>&1; echo