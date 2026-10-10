"""65高さの地面HDMA生成を専用コード化し、未使用LoROM領域へ配置する。"""
import json
import struct


def build(assets, dest):
    offsets = struct.unpack('<65H', (assets / 'ground_horizontal_run_offsets.bin').read_bytes())
    runs = (assets / 'ground_horizontal_runs.bin').read_bytes()
    value_offsets = struct.unpack('<128H', (assets / 'ground_horizontal_offsets.bin').read_bytes())
    values = (assets / 'ground_horizontal.bin').read_bytes()
    rom = bytearray(65536)
    cursor = 256
    pointers = bytearray()
    checked = 0
    for height, start in enumerate(offsets):
        code = bytearray()
        operations = []
        output = 0
        def constant(value):
            nonlocal output
            code.extend(b'\xa9' + bytes([value]) + b'\x99' + struct.pack('<H', output))
            operations.append((output, value, False))
        horizon = 104 + height
        headers = (127, horizon - 127) if horizon >= 128 else (horizon,)
        for length in headers:
            constant(length)
            output += 1
            constant(128)
            output += 2
        while runs[start]:
            length, index = runs[start:start + 2]
            constant(length)
            output += 1
            code.extend(b'\xbf' + struct.pack('<H', index) + b'\x00\x99' + struct.pack('<H', output))
            operations.append((output, index, True))
            output += 2
            start += 2
        constant(0)
        code += b'\x6b'
        if cursor < 32768 and cursor + len(code) > 32768:
            cursor = 32768
        assert cursor + len(code) <= 65536
        absolute = 65536 + cursor
        address = ((absolute // 32768) << 16) | 32768 | (absolute & 32767)
        pointers += address.to_bytes(3, 'little')
        rom[cursor:cursor + len(code)] = code
        cursor += len(code)
        for phase, value_start in enumerate(value_offsets):
            actual = bytearray(270)
            for position, value, indexed in operations:
                actual[position] = values[value_start + value] if indexed else value
            expected = bytearray()
            for length in headers:
                expected += bytes((length, 128, 0))
            position = offsets[height]
            while runs[position]:
                length, index = runs[position:position + 2]
                expected += bytes((length, values[value_start + index], 0))
                position += 2
            expected += b'\x00'
            assert actual[:len(expected)] == expected
            checked += 1
    (dest / 'ground_compiled.bin').write_bytes(rom)
    (dest / 'ground_compiled_pointers.bin').write_bytes(pointers)
    (dest / 'ground_compiled_packing.json').write_text(json.dumps({'bytes': cursor, 'tablesChecked': checked, 'preservedZeroBytes': 256}, indent=2) + '\n')


def transform(text):
    text = '.import sa1_ground_compiled\n' + text
    first = text.index('  lda _fx_ground_hptr\n  sta hp', text.index('  sta hv\n'))
    last = text.index('ground_done:\n', first)
    return text[:first] + '  ldx hv\n  ldy _fx_ground_hptr\n  jsr sa1_ground_compiled\n' + text[last:]
