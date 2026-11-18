"""Conservative Windows paths; checked before runs and checkpoint publication."""
import ntpath,re,sys
from pathlib import Path

def units(s):return len(str(s).encode('utf-16-le'))//2

def check_workspace(paths,windows=None):
 if windows is None:windows=sys.platform=='win32'
 if windows:
  for p in paths:
   if units(Path(p).resolve())>120:
    raise ValueError('Working folder is too deep for this package. Extract B.zip to C:\\S and use a short output folder such as r.')

def check_archive(names,destination='C:\\S'):
 seen=set()
 for name in names:
  parts=name.split('/')
  if not name.isascii() or len(name)>24 or name.startswith('/') or any(x in ['','..','.'] for x in parts):raise ValueError('Unsafe or long archive path: '+name)
  if name.casefold() in seen:raise ValueError('Duplicate archive path: '+name)
  seen.add(name.casefold())
  for part in parts:
   if re.search(r'[<>:"\\|?*]',part) or part.endswith((' ','.')) or re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',part):raise ValueError('Invalid Windows name: '+part)
  if units(ntpath.join(destination,*parts))>=200:raise ValueError('Extract to a shorter destination such as C:\\S')
 return {'entries':len(names),'max_relative_characters':max(map(len,names),default=0),'max_full_characters_at_destination':max((units(ntpath.join(destination,*n.split('/'))) for n in names),default=0),'destination':destination}
