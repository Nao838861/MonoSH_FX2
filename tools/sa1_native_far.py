"""原画を変えず、反転共有で地面と遠景をVRAMへ配置する。"""
import json
import struct
import numpy as np


def decode(data, bpp):
    pixels = np.zeros((8, 8), dtype=np.uint8)
    for plane in range(bpp):
        for y in range(8):
            value = data[plane // 2 * 16 + y * 2 + plane % 2]
            for x in range(8):
                pixels[y, x] |= ((value >> (7 - x)) & 1) << plane
    return pixels


def encode(pixels, bpp):
    result = bytearray(bpp * 8)
    for plane in range(bpp):
        for y in range(8):
            result[plane // 2 * 16 + y * 2 + plane % 2] = sum(
                ((int(pixels[y, x]) >> plane) & 1) << (7 - x) for x in range(8))
    return bytes(result)


def canonical(pixels):
    choices = [(pixels, 0), (pixels[:, ::-1], 0x4000),
               (pixels[::-1], 0x8000), (pixels[::-1, ::-1], 0xc000)]
    return min((p.tobytes(), flip) for p, flip in choices)


def ground_pixel(ppu, entry):
    address = 0xc000 + (entry & 1023) * 16
    pixels = decode(ppu[address:address + 16], 2)
    if entry & 0x4000:
        pixels = pixels[:, ::-1]
    if entry & 0x8000:
        pixels = pixels[::-1]
    return pixels


def build(ppu, background, dest, dynamic=False):
    original = bytes(ppu)
    pool = {}
    ground_map = struct.unpack('<2048H', original[0xf000:])
    for slot, entry in enumerate(ground_map):
        address = 0xc000 + (entry & 1023) * 16
        key, flip = canonical(decode(original[address:address + 16], 2))
        if key not in pool:
            pool[key] = 256 + len(pool)
        mapped = pool[key] | ((entry & 0xfc00) ^ flip)
        struct.pack_into('<H', ppu, 0xf000 + slot * 2, mapped)
    for key, tile in pool.items():
        ppu[0xc000 + tile * 16:0xc000 + tile * 16 + 16] = encode(
            np.frombuffer(key, dtype=np.uint8).reshape(8, 8), 2)
    ground_end = 0xd000 + len(pool) * 16
    for slot, entry in enumerate(ground_map):
        mapped = struct.unpack_from('<H', ppu, 0xf000 + slot * 2)[0]
        assert np.array_equal(ground_pixel(original, entry), ground_pixel(ppu, mapped))

    # BG2の64列mapは、BG1が使わないrow24/25だけを参照する。
    # 二枚目mapのCE00..CE7Fを避けてCHRを割り当てる。
    addresses = list(range(0xcb80, 0xce00, 32)) + list(range(0xce80, 0xd000, 32))
    addresses += list(range((ground_end + 31) & ~31, 0xf000, 32))
    far = np.zeros((16, 512), dtype=np.uint8)
    far[:14] = np.frombuffer(background[:14 * 512], dtype=np.uint8).reshape(14, 512)
    far_pool = {}
    for row in range(2):
        for col in range(64):
            pixels = far[row * 8:row * 8 + 8, col * 8:col * 8 + 8]
            key, flip = canonical(pixels)
            if key not in far_pool:
                assert len(far_pool) < len(addresses), 'native far does not fit VRAM'
                far_pool[key] = addresses[len(far_pool)]
                address = far_pool[key]
                ppu[address:address + 32] = encode(np.frombuffer(key, dtype=np.uint8).reshape(8, 8), 4)
            address = far_pool[key]
            entry = (address - 0xc000) // 32 | 0x0400 | flip
            map_address = 0xc000 + (col // 32) * 0x800 + (24 + row) * 64 + (col % 32) * 2
            struct.pack_into('<H', ppu, map_address, entry)
            actual = decode(ppu[address:address + 32], 4)
            if flip & 0x4000:
                actual = actual[:, ::-1]
            if flip & 0x8000:
                actual = actual[::-1]
            assert np.array_equal(actual, pixels)
    if dynamic:
        for row in range(2):
            for col in range(64):
                address=addresses[row*32+(col%32)]
                entry=(address-0xc000)//32 | 0x0400
                map_address=0xc000+(col//32)*0x800+(24+row)*64+(col%32)*2
                struct.pack_into('<H',ppu,map_address,entry)
    report = {'groundTiles': len(pool), 'groundEnd': hex(ground_end),
              'farTiles': len(far_pool), 'farBytes': len(far_pool) * 32,
              'farChrAddresses': addresses[:64] if dynamic else list(far_pool.values()),'dynamicCombined':dynamic, 'groundMapPixelMatches': 2048,
              'farTilePixelMatches': 128}
    (dest / 'native_far_packing.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return ppu
