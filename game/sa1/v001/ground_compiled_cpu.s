.setcpu "65816"
.smart
.export sa1_ground_compiled
.import _monosh_ground_offset
.segment "BOOT"
ground_programs: .incbin "ground_compiled_pointers.bin"
.segment "CODE"
sa1_ground_compiled:
  rep #$30
  phx
  lda _monosh_ground_offset
  and #255
  sta $013e
  asl
  clc
  adc $013e
  tax
  lda f:ground_programs,x
  sta f:$7f0001+ground_program_gate
  sep #$20
  lda f:ground_programs+2,x
  sta f:$7f0003+ground_program_gate
  plx
  jsl $7f0000+ground_program_gate
  rts
ground_program_gate:
  jml $028100
