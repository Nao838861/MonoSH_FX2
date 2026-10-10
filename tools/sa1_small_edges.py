"""幅2〜32byteの退避・復元ループを、各256byteの内部RAMコードへ生成する。"""
import struct


def build(dest):
    result = bytearray()
    for width in range(2, 33, 2):
        first = 4 + (16 - width // 2) * 8
        for restore in (False, True):
            code = bytearray((0x80, first - 2, 0xea, 0xea))
            for block in range(16):
                offset = (block - (16 - width // 2)) * 2
                if offset < 0:
                    code += bytes([0xea]) * 8
                elif restore:
                    code += b'\xb9' + struct.pack('<H', offset)
                    code += b'\x9f' + struct.pack('<H', offset) + b'\x40\xea'
                else:
                    code += b'\xbf' + struct.pack('<H', offset) + b'\x40'
                    code += b'\x99' + struct.pack('<H', offset) + b'\xea'
            code += b'\x8a\x18\x69\x80\x00\xaa'
            code += b'\x98\x18\x69' + struct.pack('<H', width) + b'\xa8'
            code += b'\xc6\xce\xf0\x03\x82'
            code += struct.pack('<h', first - (len(code) + 2)) + b'\x6b'
            assert len(code) <= 256
            result += code + bytes([0xea]) * (256 - len(code))
    assert len(result) == 8192
    (dest / 'small_edge_templates.bin').write_bytes(result)


def transform(text):
    text = '.setcpu "65816"\n.import sa1_small_edge_prepare: far, sa1_small_edge_save: far, sa1_small_edge_restore: far\n' + text
    text = text.replace('edge_return:\n  rtl', 'edge_return:\n  jsl sa1_small_edge_prepare\n  rtl', 1)
    text = text.replace('cmp #9\n  bcc edge_', 'cmp #33\n  bcc edge_')
    text = text.replace('edge_save_cpu:\n', 'edge_save_cpu:\n  lda $c4\n  cmp #33\n  bcs :+\n  jsl sa1_small_edge_save\n  rtl\n:\n', 1)
    text = text.replace('edge_restore_cpu:\n', 'edge_restore_cpu:\n  lda $c4\n  cmp #33\n  bcs :+\n  jsl sa1_small_edge_restore\n  rtl\n:\n', 1)
    return text
