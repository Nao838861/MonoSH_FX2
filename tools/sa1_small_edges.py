"""幅2〜32byteの退避・復元ループを、各256byteの内部RAMコードへ生成する。"""
import struct


def build(dest, wide=False):
    result = bytearray()
    blocks = 32 if wide else 16
    stride = 7 if wide else 8
    for width in range(2, blocks * 2 + 1, 2):
        first = 4 + (blocks - width // 2) * stride
        for restore in (False, True):
            code = bytearray((0x82,)) + struct.pack('<h', first - 3) + b'\xea' if wide else bytearray((0x80, first - 2, 0xea, 0xea))
            for block in range(blocks):
                offset = (block - (blocks - width // 2)) * 2
                if offset < 0:
                    code += bytes([0xea]) * stride
                elif restore:
                    code += b'\xb9' + struct.pack('<H', offset)
                    code += b'\x9f' + struct.pack('<H', offset) + b'\x40'
                    if not wide: code += b'\xea'
                else:
                    code += b'\xbf' + struct.pack('<H', offset) + b'\x40'
                    code += b'\x99' + struct.pack('<H', offset)
                    if not wide: code += b'\xea'
            code += b'\x8a\x18\x69\x80\x00\xaa'
            code += b'\x98\x18\x69' + struct.pack('<H', width) + b'\xa8'
            code += b'\xc6\xce\xf0\x03\x82'
            code += struct.pack('<h', first - (len(code) + 2)) + b'\x6b'
            assert len(code) <= 256
            result += code + bytes([0xea]) * (256 - len(code))
    assert len(result) == blocks * 512
    (dest / 'small_edge_templates.bin').write_bytes(result)


def transform(text, wide=False):
    text = '.setcpu "65816"\n.import sa1_small_edge_prepare: far, sa1_small_edge_save: far, sa1_small_edge_restore: far\n' + text
    text = text.replace('edge_return:\n  rtl', 'edge_return:\n  jsl sa1_small_edge_prepare\n  rtl', 1)
    text = text.replace('cmp #9\n  bcc edge_', 'cmp #33\n  bcc edge_')
    text = text.replace('edge_save_cpu:\n', 'edge_save_cpu:\n  lda $c4\n  cmp #33\n  bcs :+\n  jsl sa1_small_edge_save\n  rtl\n:\n', 1)
    text = text.replace('edge_restore_cpu:\n', 'edge_restore_cpu:\n  lda $c4\n  cmp #33\n  bcs :+\n  jsl sa1_small_edge_restore\n  rtl\n:\n', 1)
    if wide: text = text.replace('cmp #33', 'cmp #65')
    return text


def wide_source(text):
    assert text.count('cmp #33') == 1
    assert text.count('.repeat 8') == 1
    assert text.count('cpx #128') == 1
    return text.replace('cmp #33', 'cmp #65').replace('.repeat 8', '.repeat 7').replace('cpx #128', 'cpx #224')
