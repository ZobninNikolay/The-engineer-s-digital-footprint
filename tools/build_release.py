from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.git','.venv','__pycache__','workspace'}
def files():
 return [p for p in sorted(ROOT.rglob('*')) if p.is_file() and not p.is_symlink() and not any(x in EXCLUDE for x in p.relative_to(ROOT).parts) and p.name!='MANIFEST.json' and p.suffix not in ('.pyc',)]
def build():
 all_files=files();manifest={'release':'2.0.0','files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in all_files}}
 (ROOT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 out=ROOT.parent/'DT_Release_v2_0.zip'
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in all_files+[ROOT/'MANIFEST.json']:z.write(p,p.relative_to(ROOT).as_posix())
 print(json.dumps({'archive':str(out),'size_bytes':out.stat().st_size,'files':len(all_files)+1,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
if __name__=='__main__':build()
