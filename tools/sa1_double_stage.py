"""投影表をROMへ移し、7E/7Fの二つの変換先を使う。"""
from sa1_vram_four import change

def projection(text):
 text=text.replace('f:$7f0000+projection_rows','f:projection_rows')
 text=text.replace('f:$7f0000+projection_scales','f:projection_scales')
 return change(text,'projection_rows:\n  .incbin "assets/projection_rows.bin"\nprojection_scales:\n  .incbin "assets/projection_scales.bin"',
               'projection_rows=$df0000\nprojection_scales=$df6f00')

def stage(text):
 text=change(text,'stage_busy: .res 2','stage_busy: .res 2\nstage_busy2: .res 2\nstage_wram_bank: .res 2\nstage_chr_base: .res 2\nstage_map_base: .res 2')
 text=change(text,'  lda stage_busy\n  jne pipe_stage_done', '''  lda stage_busy
  beq double_stage_a
  lda stage_busy2
  jne pipe_stage_done
  lda #$7f
  sta stage_wram_bank
  lda #$c600
  sta stage_chr_base
  lda #$c000
  sta stage_map_base
  bra double_stage_selected
double_stage_a:
  lda #$7e
  sta stage_wram_bank
  lda #$cb00
  sta stage_chr_base
  lda #$c500
  sta stage_map_base
double_stage_selected:''')
 text=change(text,'  lda #$cb20\n  sta stage_output','  lda stage_chr_base\n  clc\n  adc #32\n  sta stage_output')
 text=change(text,'  ldx #0\n  lda #0\nstage_zero:\n  sta a:$cb00,x\n  inx\n  inx\n  cpx #32\n  bcc stage_zero', '''  lda stage_wram_bank
  cmp #$7e
  bne double_zero_b
  ldx #0
  lda #0
double_zero_a_loop:
  sta f:$7ecb00,x
  inx
  inx
  cpx #32
  bcc double_zero_a_loop
  bra double_zero_done
double_zero_b:
  ldx #0
  lda #0
double_zero_b_loop:
  sta f:$7fc600,x
  inx
  inx
  cpx #32
  bcc double_zero_b_loop
double_zero_done:''')
 text=change(text,'  lda #$cb20\n  sta f:$002181','  lda stage_chr_base\n  clc\n  adc #32\n  sta f:$002181')
 text=change(text,'  lda #0\n  sta f:$002183','  lda stage_wram_bank\n  and #1\n  sta f:$002183')
 text=change(text,'  lda #$c500\n  sta f:$002181','  lda stage_map_base\n  sta f:$002181')
 text=change(text,'  lda #$007e\n  sta pipe_records,x','  lda stage_wram_bank\n  sta pipe_records,x')
 text=change(text,'  sbc #$cb00\n','  sbc stage_chr_base\n')
 text=change(text,'  lda #$cb00\n  sta pipe_records+210,x','  lda stage_chr_base\n  sta pipe_records+210,x')
 text=change(text,'  lda #$c500\n  sta pipe_records+216,x','  lda stage_map_base\n  sta pipe_records+216,x')
 text=change(text,'  lda #1\n  sta pipe_records+38,x\n  sta stage_busy', '''  lda stage_wram_bank
  cmp #$7f
  beq double_stage_b_busy
  lda #1
  sta stage_busy
  bra double_stage_set_tag
double_stage_b_busy:
  lda #2
  sta stage_busy2
double_stage_set_tag:
  sta pipe_records+38,x''')
 return text

def pipeline(text):
 text=change(text,'  .ifdef SA1_STAGED\n  lda #$7e\n  .else\n  lda pipe_records,x\n  .endif\n  sta f:$004304',
             '  lda pipe_records,x\n  sta f:$004304')
 return change(text,'  stz stage_busy\n', '''  ldx pipe_record_offset
  lda pipe_records+38,x
  cmp #2
  bne :+
  stz stage_busy2
  bra :++
:
  stz stage_busy
:
''')

def draw_phase_stage(text):
 text=change(text,'pipe_stage_convert:\n  rep #$30\n','''pipe_stage_convert:
  rep #$30
  lda f:$00319e
  bne stage_phase_ok
  lda f:$003100
  jne pipe_stage_done
stage_phase_ok:
''')
 return change(text,'  cmp #203\n  bcs stage_time_ok','  cmp #197\n  jcs pipe_stage_done')

def draw_phase_renderer(text):
 text=change(text,'sa1_clear_start:\n','sa1_clear_start:\n  stz $019e\n')
 text=change(text,'sa1_draw_start:\n  rep #$30\n','sa1_draw_start:\n  rep #$30\n  lda #1\n  sta $019e\n')
 return change(text,'sa1_output_done:\n','sa1_output_done:\n  stz $019e\n')

def draw_phase_pipeline(text):
 begin=text.index('pipe_wait_render:\n');end=text.index('pipe_render_ready:\n',begin)
 block=text[begin:end]
 assert block.count('  wai\n')==1
 return text[:begin]+block.replace('  wai\n','  nop\n',1)+text[end:]
