
cd "$(pwd)" && python3 -c "
exec(open('run.py').read().split('def resid')[0])
quart,dbl=pick(1750.,600.,2400.)
print('Q',[(round(e),m) for e,m in quart]); print('D',[(round(e),m) for e,m in dbl[:10]])
" 2>&1 | tail -2
