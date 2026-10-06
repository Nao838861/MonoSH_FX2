"""自機全poseと自弾の縮小絵を、起動時だけ転送する4bpp OBJへ変換する。"""
import struct
from PIL import Image
from build_ground import GAME

PLAYERS = [9, *range(15, 31)]

def build():
    assets=GAME/'assets'
    vram=bytearray((assets/'ppu.bin').read_bytes())
    far=assets/'far_map.bin'
    if not far.exists():
        far.write_bytes(vram[0xc000:0xc800])
    vram[0xb000:0xb800]=far.read_bytes()
    vram[0xc000:]=bytes(0x4000)
    player_tiles=[0]*(44*6)
    bullet_tiles=[0]*17
    slot=0
    def pixels(asset):
        im=Image.open(assets/f'{asset:02d}.png').convert('RGBA')
        return [[0 if a<128 else (3 if r+g+b>=384 else 1)
                 for r,g,b,a in [im.getpixel((x,y)) for x in range(im.width)]]
                for y in range(im.height)]
    def block(pix):
        nonlocal slot
        base=(slot//64)*256+(slot%8)*2+((slot%64)//8)*32
        for ty in range(2):
            for tx in range(2):
                raw=bytearray(32)
                for y in range(8):
                    for plane in range(4):
                        pos=(plane//2)*16+y*2+(plane&1)
                        raw[pos]=sum(((pix[ty*8+y][tx*8+x]>>plane)&1)<<(7-x) for x in range(8))
                address=0xc000+(base+ty*16+tx)*32
                assert address+32<=65536,'OBJ atlas overflow'
                vram[address:address+32]=raw
        slot+=1
        return base
    for asset in PLAYERS:
        pix=pixels(asset)
        assert (len(pix[0]),len(pix))==(32,48)
        for cy in range(3):
            for cx in range(2):
                part=[row[cx*16:cx*16+16] for row in pix[cy*16:cy*16+16]]
                player_tiles[asset*6+cy*2+cx]=block(part)
    source=pixels(10)
    for size in range(1,17):
        # Q8.8最近傍。GSUが描いていた縮小画素と完全に揃える。
        du=16*256//size
        pix=[[source[(y*du)>>8][(x*du)>>8] if x<size and y<size else 0
              for x in range(16)] for y in range(16)]
        bullet_tiles[size]=block(pix)
    (assets/'obj_tiles.bin').write_bytes(struct.pack('<264H',*player_tiles))
    (assets/'obj_bullets.bin').write_bytes(struct.pack('<17H',*bullet_tiles))
    (assets/'ppu.bin').write_bytes(vram)
    print(f'OBJ atlas: {slot} blocks, {slot*128} bytes, VRAM C000-FFFF')

if __name__=='__main__':build()
