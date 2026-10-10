"""7枚の描画バッファを維持するゲーム状態配置の準備。"""
import json
import re


def configuration(text):
    text = text.replace('CPUDATA: start=$2000, size=$8000', 'CPUDATA: start=$8000, size=$8000')
    text = text.replace('  COLORRAM:', '  GAMESTATE: start=$6000, size=$1800, file="";\n  COLORRAM:')
    text = text.replace('COLORRAM: start=$A000, size=$5E00', 'COLORRAM: start=$2000, size=$4000')
    text = text.replace('  DATA: load=DATALOAD, run=CPUDATA', '  DATA: load=DATALOAD, run=GAMESTATE')
    text = text.replace('BSS: load=CPUDATA,', 'BSS: load=GAMESTATE,')
    return text


def cpu(text):
    text = '.setcpu "65816"\n.import __RODATA_SIZE__, __DATA_LOAD__, __DATA_RUN__, __DATA_SIZE__\n.import compact_ppu_boot: far\n' + text
    old = '  ldx #0\n  ldy #$2000\n  lda #$ffff\n  mvn #$c2,#$7e\n'
    assert text.count(old) == 1
    new = '''  lda #0
  ldx #0
compact_clear_wram:
  sta f:$7e0000,x
  inx
  inx
  bne compact_clear_wram
  ldx #0
  ldy #$8000
  lda #__RODATA_SIZE__-1
  mvn #$c2,#$7e
  ldx #.loword(__DATA_LOAD__)
  ldy #__DATA_RUN__
  lda #__DATA_SIZE__-1
  mvn #$c2,#$7e
'''
    text = text.replace(old, new)
    old = '  lda #$c3\n  sta $4304\n  lda #1\n  sta $420b\n'
    assert text.count(old) == 1
    return text.replace(old, '  jsl compact_ppu_boot\n', 1)


def packbits(data):
    out = bytearray()
    cursor = 0
    while cursor < len(data):
        end = cursor + 1
        while end < len(data) and data[end] == data[cursor] and end-cursor < 128:
            end += 1
        if end-cursor >= 3:
            out += bytes((0x80 + end-cursor-1, data[cursor]))
            cursor = end
        else:
            start = cursor
            cursor += 1
            while cursor < len(data) and cursor-start < 128 and not (cursor+2 < len(data) and data[cursor] == data[cursor+1] == data[cursor+2]):
                cursor += 1
            out.append(cursor-start-1)
            out += data[start:cursor]
    return out


def renderer(text):
    start = text.index('clear_scanline:\n')
    end = text.index('clear_tile_next:\n', start)
    old = text[start:end]
    assert old.count('lda #$8000') == old.count('lda #2\n  sta $2234') == 1
    return text[:start] + old.replace('lda #$8000', 'lda #$f000').replace('lda #2\n  sta $2234', 'lda #3\n  sta $2234') + text[end:]


def game_source(text):
    """ゲーム用の固定scratchをIRAMからBW-RAM窓へ移す。即値は変更しない。"""
    text = text.replace('f:$7f0000+', 'f:$c10000+')
    return re.sub(r'(?im)^(\s*(?:lda|ldx|ldy|sta|stx|sty|stz|adc|sbc|cmp|cpx|cpy|and|ora|eor|bit|inc|dec|asl|lsr|rol|ror|trb|tsb)\s+)\$0([123][0-9a-f]{2})\b',
                  lambda m: m[1]+'$'+format(int(m[2], 16)+0x7700, '04x'), text)


def math_source(text):
    """SA-1からS-CPUの乗算器へ触らず、同じ8bit積を計算する。"""
    text = game_source(text)
    start = text.index('  sta f:$004202\n')
    text = text[:start] + '''  and #255
  sta $7a84
  lda $7a82
  xba
  and #255
  sta $7a86
  stz $7a88
  ldx #8
compact_multiply:
  lsr $7a86
  bcc :+
  lda $7a88
  clc
  adc $7a84
  sta $7a88
:
  asl $7a84
  dex
  bne compact_multiply
''' + text[start+len('  sta f:$004202\n'):]
    return text.replace('lda f:$004216', 'lda $7a88')


def unpackbits(data):
    out = bytearray()
    cursor = 0
    while cursor < len(data):
        control = data[cursor]
        cursor += 1
        count = (control & 127)+1
        if control & 128:
            out += bytes((data[cursor],))*count
            cursor += 1
        else:
            out += data[cursor:cursor+count]
            cursor += count
    return out


def relocate_ground_pointers(build):
    path = build/'ground_compiled_pointers.bin'
    data = bytearray(path.read_bytes())
    for offset in range(0, len(data), 3):
        old = int.from_bytes(data[offset:offset+3], 'little')
        physical = (old >> 16)*0x8000 + (old & 0x7fff)
        assert 0x10000 <= physical < 0x20000
        data[offset:offset+3] = (0xc30000 + physical-0x10000).to_bytes(3, 'little')
    path.write_bytes(data)


def finish(rom, build, labels, ppu):
    packed = packbits(ppu)
    assert unpackbits(packed) == ppu
    assert len(packed) <= 0x8000
    assert labels['__RODATA_SIZE__']+labels['__DATA_SIZE__'] <= 0x8000
    assert labels['__BSS_RUN__']+labels['__BSS_SIZE__'] <= 0x7800
    rom[0x10000:0x10000+labels['__RODATA_SIZE__']] = rom[0x420000:0x420000+labels['__RODATA_SIZE__']]
    rom[0x428000:0x428000+len(packed)] = packed
    rom[0x430000:0x440000] = (build/'ground_compiled.bin').read_bytes()
    assert rom[0x1f000:0x1f400] == bytes(1024), 'clear DMA zero source was overwritten'
    (build/'compact_memory.json').write_text(json.dumps({
        'ppuPackedBytes': len(packed), 'ppuBytes': len(ppu),
        'rodataBytes': labels['__RODATA_SIZE__'],
        'bssEnd': labels['__BSS_RUN__']+labels['__BSS_SIZE__'],
        'groundBank': 0xc3, 'framebufferSlots': 7,
    }, indent=2)+'\n')
