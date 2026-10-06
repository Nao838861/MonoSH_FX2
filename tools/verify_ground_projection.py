"""格子境界が同じ消失点からの直線に沿うことを、atlasとHDMA表で検査する。"""
import json
import math
import struct
from build_game import BUILD,GAME
from verify_game_display import pixel,hdma

def verify():
    vram=(GAME/'assets/ppu.bin').read_bytes()
    scroll=(GAME/'assets/ground_scroll.bin').read_bytes()
    offsets=struct.unpack('<65H',(GAME/'assets/ground_scroll_offsets.bin').read_bytes())
    horizontal=(GAME/'assets/ground_horizontal.bin').read_bytes()
    transitions={}
    for row in range(1,81):
        colors=[pixel(vram,1,x,127+row) for x in range(512)]
        transitions[row]=[x for x in range(1,512) if colors[x]!=colors[x-1]]
    max_error=0;checked=0
    for offset,start in enumerate(offsets):
        table=hdma(scroll[start:],2)
        horizon=104+offset;span=204-horizon
        for physical in range(horizon+5,205):
            source=physical+struct.unpack('<h',table[physical])[0]
            row=source-127
            assert 1<=row<=80
            for phase in [0,32,64,96,127]:
                h=horizontal[phase*81+row]
                for stripe in range(-4,5):
                    # 消失点(128,horizon)、下端の格子幅51px。境界ごとの
                    # 直線を画面座標から求め、実タイルの色境界へ照合する。
                    ideal=128+(stripe-phase/64)*51*(physical-horizon)/span
                    if not 2<ideal<254:continue
                    source_boundary=math.ceil(256+stripe*row*51/80)
                    assert source_boundary in transitions[row],(row,stripe)
                    error=abs(source_boundary-h-ideal)
                    max_error=max(max_error,error);checked+=1
    # |stripe-phase/64|<6、source行の丸め<=0.5行、境界/Hの整数化各<1px。
    # 6*51/80*0.5+2 < 4px。曲線の表を流用した旧方式はこの上限を超える。
    assert max_error<4.0,f'curved ground beyond raster quantization: {max_error}px'
    out={'cameraOffsets':65,'horizontalPhases':[0,32,64,96,127],
         'checkedBoundaries':checked,'maxRasterQuantizationErrorPx':max_error,
         'note':'同一消失点の一次式。81source行と整数画素への量子化の差を含む'}
    (BUILD/'ground_projection.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Ground: {checked} boundaries, max linear projection error {max_error:.3f}px')

if __name__=='__main__':verify()
