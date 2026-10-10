"""ゲーム状態のBW40分離とSA-1専用入口を生成する。"""

SLOTS=(0x0441,0x0442,0x8441,0x8442,0x8443)


def five_slots(name,text):
    if name=='occupancy':
        text=text.replace('cmp #7','cmp #5').replace('adc #5','adc #3').replace('sbc #7','sbc #5')
        lines=text.splitlines(True)
        text=''.join(line for line in lines if not any(f'${0x432000+i*96+offset:06x},x' in line for i in (5,6) for offset in (0,2)))
    if name=='background_cache':
        text=text.replace('cmp #14','cmp #10').replace('.word $0440,$0441,$0442,$8440,$8441,$8442,$8443','.word $0441,$0442,$8441,$8442,$8443')
    return text


def cpu_pipeline(text):
    return text.replace('  cmp #14\n','  cmp #10\n').replace('.word $0440,$0441,$0442,$8440,$8441,$8442,$8443','.word $0441,$0442,$8441,$8442,$8443')


def frame(text):
    text=text.replace('.export _fx_frame','.export sa1_game_frame').replace('_fx_frame:', 'sa1_game_frame:')
    text=text.replace('.import _fx_read_input,','.import sa1_game_input,').replace('CALL_C _fx_read_input','CALL_C sa1_game_input')
    text=text.replace('  jsr _fx_build_ground\n','')
    return text

