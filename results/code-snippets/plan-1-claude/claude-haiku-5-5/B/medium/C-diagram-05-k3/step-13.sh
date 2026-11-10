cd <SANDBOX_TMP>/ts && python3 -c "
exec(open('final.py').read().split('table = {}')[0])
print([(n,round(e,5)) for e,n in lo[:8]])
" 2>&1 | tail -1