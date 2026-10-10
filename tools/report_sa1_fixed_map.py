"""固定マップ、未使用履歴の削除、敵弾コード再利用の比較を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_fixed_map'
CASES=(
 'movestress_detinput_bulletopaque8_guard2_tracepalette',
 'movestress_detinput_fixedmap_v3_tracepalette',
 'movestress_detinput_fixedmap_v1_long_tracepalette',
 'bossmovestress_detinput_fixedmap_v1_tracepalette',
 'leftfixture_fixedmap_leftscan_v1_tracepalette',
 'movestress_detinput_fixedmap_leftscan_v1_tracepalette',
 'movestress_detinput_fixedmap_nohistory_v1_tracepalette',
 'movestress_detinput_fixedmap_resident_v1_tracepalette',
 'bossmovestress_detinput_fixedmap_resident_v1_tracepalette',
 'flipfixture_fixedmap_resident_v1_tracepalette',
)


def main():
 DEST.mkdir(parents=True,exist_ok=True)
 reference=packets(CASES[0]);cases=[]
 for name in CASES:
  s=json.loads((BUILD/name/'summary.json').read_text())
  assert s['pixelMatchedPresents']>=120
  assert not (BUILD/name/'failure.txt').exists()
  e={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','romSha256',
   'irqMathRegistersVerified','goal60fpsAchieved','presentationFieldIntervals')}
  e.update(scenario=name,firstVisibleField=s['presentationTimes'][0]['visibleField'],
   maxSa1Ms=max(j['totalSa1Ms'] for j in s['sa1Jobs']),
   maxOutputMs=max(j['totalOutputMs'] for j in s['outputJobs']))
  if name.startswith('movestress_detinput'):
   actual=packets(name);n=min(len(reference),len(actual));assert reference[:n]==actual[:n]
   e['logicMatchedGenerations']=n
  cases.append(e)
 archive=DEST/'evidence.zip'
 folders=('bulletopaque8_guard2_build','fixedmap_v1_build',
  'fixedmap_leftscan_v1_build','fixedmap_nohistory_v1_build','fixedmap_resident_v1_build')
 failed='movestress_detinput_bulletopaque8_v2_tracepalette'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in (*CASES,failed):
   for p in sorted((BUILD/name).iterdir()):
    if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
  for folder in folders:
   for p in sorted((BUILD/folder).iterdir()):
    if p.is_file():z.write(p,folder+'/'+p.name)
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 report={'cases':cases,'goal60fpsAchieved':False,
  'excludedFailure':{'scenario':failed,'reason':(BUILD/failed/'failure.txt').read_text(),
   'performanceComparisonEligible':False},
  'evidenceSha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
 (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
 print({'cases':len(cases),'archiveBytes':archive.stat().st_size,'sha256':report['evidenceSha256']})


if __name__=='__main__':main()
