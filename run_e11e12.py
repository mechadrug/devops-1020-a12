"""Host entry; installed alongside E8-E10 files without replacing run_lab.py."""
import argparse,json,os,re,subprocess
from pathlib import Path

root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('stage',choices=['build','prepare','run','serve','test']);p.add_argument('--request');p.add_argument('--out');p.add_argument('--port',type=int,default=8080);a=p.parse_args()
if os.name!='posix':p.error('Run on the Linux cloud host after SSH login')
sid=subprocess.check_output(['git','config','--local','user.name'],cwd=root,text=True).strip()
if not re.fullmatch(r'[0-9]{6,16}',sid):p.error('Set local git user.name to your numeric student ID')
image='course-e11e12:'+sid
if a.stage=='build':
    cmd=['docker','build','-f',str(root/'labs/e11e12/environment/services/buildchecker/Dockerfile'),'-t',image,str(root/'labs/e11e12/environment')]
else:
    socket=['--network','bridge','--group-add',str(Path('/var/run/docker.sock').stat().st_gid),'-v','/var/run/docker.sock:/var/run/docker.sock'] if a.stage in ('run','serve') else ['--network','none']
    network=['-p',f'127.0.0.1:{a.port}:8080'] if a.stage=='serve' else []
    cmd=['docker','run','--rm',*socket,*network,'--cap-add','SYS_PTRACE','--user',f'{os.getuid()}:{os.getgid()}','-e','HOME=/tmp','-e','PYTHONPATH=/course/labs/e11e12:/course/labs/e8e10:/course/labs/e11e12/vendor:/app','-v',str(root)+':/course','-w','/course',image,'python3']
    if a.stage=='prepare':cmd+=['labs/e11e12/prepare.py']
    elif a.stage=='serve':cmd+=['labs/e11e12/server.py','--host','0.0.0.0']
    elif a.stage=='test':cmd+=['-m','unittest','discover','-s','labs/e11e12','-p','test_*.py','-v']
    else:
        if not a.request or not a.out:p.error('--request and --out required')
        request=(root/a.request).resolve();out=(root/a.out).resolve()
        if not request.is_relative_to(root) or not out.is_relative_to(root/'work') or out==root/'work':p.error('Request inside repo and output below work/ required')
        cmd+=['labs/e11e12/pipeline.py','--request','/course/'+str(request.relative_to(root)),'--out','/course/'+str(out.relative_to(root))]
print('IMAGE='+image,flush=True)
raise SystemExit(subprocess.call(cmd,cwd=root))
