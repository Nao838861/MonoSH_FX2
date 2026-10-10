"""敵弾の共有透明形状コードの実測と画面一致の証跡を保存する。"""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_bullet_shapes'
CASES=(
 'flipfixture_bulletshapes_v2_tracepalette',
 'flipfixture_bulletshapes_v4_clip_tracepalette',
 'movestress_bulletshapes_v5_long_tracepalette',
 'bossmovestress_bulletshapes_v5_tracepalette',
 'flipfixture_bulletshapes_v6_rom_tracepalette',
 'movestress_bulletshapes_v6_rom_tracepalette',
 'movestress_detinput_bulletshapes_v6_rom_tracepalette',
 'bossmovestress_bulletshapes_v6_rom_tracepalette',
)


def main():
 DEST.mkdir(parents=True,exist_ok=True)
 cases=[]
 for name in CASES:
  s=json.loads((BUILD/name/'summary.json').read_text())
  assert s['pixelMatchedPresents']>=120
  assert not (BUILD/name/'failure.txt').exists()
  e={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','romSha256',
   'irqMathRegistersVerified','goal60fpsAchieved','presentationFieldIntervals')}
  e.update(scenario=name,maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']))
  cases.append(e)
 archive=DEST/'evidence.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in CASES:
   for p in sorted((BUILD/name).iterdir()):
    if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
  for folder in ('bulletshapes_v2_build','bulletshapes_v4_build','bulletshapes_v5_build','bulletshapes_v6_build'):
   for p in sorted((BUILD/folder).iterdir()):
    if p.is_file():z.write(p,folder+'/'+p.name)
  z.write(BUILD/'bullet_shapes_verified.json','bullet_shapes_verified.json')
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 report={'cases':cases,'goal60fpsAchieved':False,
  'evidenceSha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
 (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
 print({'cases':len(cases),'archiveBytes':archive.stat().st_size,'sha256':report['evidenceSha256']})


if __name__=='__main__':main()
