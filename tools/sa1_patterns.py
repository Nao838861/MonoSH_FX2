"""ゲームが指定する全縮小寸法を固定upstreamと既存fixtureから抽出する。"""
import json
import re
from collections import defaultdict
from PIL import Image
from build_sa1_probe import ROOT, ART
from smooth_depth import transform, parse_table, open_enemy_sizes

def dimensions():
    result=defaultdict(set)
    for i in range(44):result[i].add(Image.open(ART/f'{i:02d}.png').size)
    sources={name:transform(name,(ROOT/f'game/v001/upstream/{name}.c').read_text()) for name in ('monosh_stage_data','monosh_enemy_data','monosh_boss_data')}
    def add(name,table,assets,stride=2):
        _,v=parse_table(sources[name],table)
        for i in assets:result[i].update(zip(v[::stride],v[1::stride]))
    for i,name in enumerate(('bush0','bush1','flystone','em0','tree0','bom0')):
        add('monosh_stage_data','stage_'+name+'_geometry',[i] if i!=5 else [5,39,40,41],4)
    for table,assets in [('enemy',[3]),('bom',[5,39,40,41]),('em1_closed',[11]),('ebullet_animation',[6,7,8,37]),('ebullet4',[31])]:
        add('monosh_enemy_data','monosh_'+table+'_geometry',assets)
    for table,assets in [('body',[13]),('face',[14]),('bom',[5,39,40,41])]:
        add('monosh_boss_data','monosh_boss_'+table+'_geometry',assets)
    raw=open_enemy_sizes(sources['monosh_enemy_data'])
    for pose,asset in enumerate((32,33,34,35,36)):
        for z in range(111):result[asset].add(tuple(raw[z*10+pose*2:z*10+pose*2+2]))
    # packet.sで自弾をカラー素材の縦横比へ変換した後の寸法も含める。
    packet=(ROOT/'game/v001/packet.s').read_text(encoding='utf-8').split('color_bullet_dimensions:',1)[1].split('.endif',1)[0]
    for word in re.findall(r'\$([0-9a-fA-F]{4})',packet):
        v=int(word,16)
        if v:result[10].add((v&255,v>>8))
    result[42].add((88,38))
    # 最大描画数/サイズのfixtureも同じ生成対象に含める。
    from test_sa1_probe import jobs
    for job in jobs():
        for _,_,w,h,asset,*_ in job['draws']:
            if w and h:result[asset].add((w,h))
    return dict(result)

def summary():
    patterns=dimensions()
    n=sum(len(v) for v in patterns.values())
    full=sum(w*h*(3 if a in (6,7,8,31,37) else 1) for a,vals in patterns.items() for w,h in vals)
    horizontal=sum(sum({w for w,h in vals})*Image.open(ART/f'{a:02d}.png').height*(3 if a in (6,7,8,31,37) else 1) for a,vals in patterns.items())
    return {'patterns':n,'fullPrescaledBytePixels':full,'fullPrescaled4bppBytes':(full+1)//2,'horizontalBytePixels':horizontal,'bwRamBytes':262144,'sizes':{str(k):sorted(v) for k,v in patterns.items()}}

if __name__=='__main__':
    s=summary();print(json.dumps({k:v for k,v in s.items() if k!='sizes'},indent=2))
