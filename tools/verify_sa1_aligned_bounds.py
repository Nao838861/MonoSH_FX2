"""完成ROMから縦8位相の範囲表を読み戻し、原画像の縮小結果と照合する。"""
import hashlib
import json
import struct
import numpy as np
from build_sa1_game import BUILD
from build_sa1_probe import assets
from sa1_patterns import dimensions


def physical(address):
    bank, low = address >> 16, address & 65535
    if bank >= 0xc0:
        return 0x400000 + (bank - 0xc0) * 65536 + low
    if bank >= 0x80:
        return 0x200000 + (bank - 0x80) * 32768 + (low & 32767)
    return bank * 32768 + (low & 32767)


def main():
    rom = (BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    config = json.loads((BUILD/'manifest.json').read_text())
    assert config['rowDirtyAligned']
    assert hashlib.sha256(rom).hexdigest() == config['romSha256']
    variants = assets()
    checked = 0
    for asset, sizes in dimensions().items():
        for w, h in sizes:
            block = 0x7f0000 + struct.unpack_from('<H', rom, 0x7f0000 + asset*512 + w*2)[0]
            entries = [block+1+i*10 for i in range(rom[block])]
            record = next(entry for entry in entries if rom[entry] == h)
            pointer = int.from_bytes(rom[record+7:record+10], 'little')
            if w < 32 or h < 24:
                assert pointer == 0
                continue
            occupied = np.zeros((h, w), dtype=bool)
            for phase in range(3 if (asset, 1) in variants else 1):
                pixels = variants[asset, phase][1]
                ah, aw = pixels.shape
                ys = (np.arange(h)*(ah*256//h)) >> 8
                xs = (np.arange(w)*(aw*256//w)) >> 8
                occupied |= pixels[ys[:, None], xs[None, :]] != 0
            table = physical(pointer)
            for phase in range(8):
                source = physical(int.from_bytes(rom[table+phase*3:table+phase*3+3], 'little'))
                decoded = []
                total = (phase+h+7)//8
                while len(decoded) < total:
                    if config.get('rowDirtyExact'):
                        left,right,length=rom[source:source+3];source+=3;decoded.extend([(left,right)]*length)
                    else:
                        value = struct.unpack_from('<H', rom, source)[0]
                        source += 2
                        decoded.extend([(value & 63, (value >> 6) & 127)] * ((value >> 13)+1))
                expected = []
                for start in range(-phase, h, 8):
                    _, xs = np.nonzero(occupied[max(0, start):min(h, start+8)])
                    pair=((int(xs.min()),int(xs.max())+1) if config.get('rowDirtyExact') else (int(xs.min())//4,(int(xs.max())+4)//4)) if len(xs) else (0,0)
                    expected.append(pair if len(xs) else (0,0))
                assert decoded == expected, (asset, w, h, phase)
                checked += 1
    result = {'romSha256': config['romSha256'], 'exactAlignedBoundsChecked': checked}
    (BUILD/'aligned_bounds_verified.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
