import argparse,os,re,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('stage',choices=['build','e8','e9','e10']);p.add_argument('--track',choices=['A','B'],default='A');p.add_argument('--out');a=p.parse_args()
sid=subprocess.check_output(['git','config','--local','user.name'],cwd=root,text=True).strip()
if not re.fullmatch(r'[0-9]{6,16}',sid):p.error('git user.name must be your numeric student ID')
image='course-e8e10:'+sid
if a.stage=='build':
 cmd=['docker','build','--progress=plain','-f',str(root/'labs/e8e10/environment/services/buildchecker/Dockerfile'),'-t',image,str(root/'labs/e8e10/environment')]
else:
 if not a.out:p.error('--out is required')
 out=(root/a.out).resolve()
 if not out.is_relative_to(root/'work') or out==root/'work':p.error('--out must be a fresh subdirectory of work/')
 if out.exists():p.error('output directory already exists; choose a new name')
 cmd=['docker','run','--rm','--network','none','--cap-add','SYS_PTRACE','--user',str(os.getuid())+':'+str(os.getgid()),'-e','HOME=/tmp','-v',str(root)+':/course','-w','/course',image,'python3','labs/e8e10/lab.py',a.stage,'--track',a.track,'--out','/course/'+str(out.relative_to(root))]
print('IMAGE='+image,flush=True)
raise SystemExit(subprocess.call(cmd,cwd=root))
