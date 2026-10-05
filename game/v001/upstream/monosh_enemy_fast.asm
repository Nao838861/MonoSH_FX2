SECTION code_compiler

PUBLIC _monosh_enemy_fast_render
PUBLIC _monosh_enemy_fast_update_bullets
PUBLIC _monosh_enemy_fast_advance
PUBLIC _monosh_enemy_fast_check_player_bullets
PUBLIC _monosh_enemy_fast_render_bullets
PUBLIC _monosh_boss_bullet_aim
PUBLIC _monosh_enemy_fast_update_em1
PUBLIC _monosh_enemy_fast_spawn_due
PUBLIC _monosh_enemy_fast_add
PUBLIC _monosh_enemy_fire_em0_fast
PUBLIC _monosh_enemy_frame

EXTERN _monosh_enemies
EXTERN _monosh_enemy_bullets
EXTERN _monosh_enemy_paths
EXTERN _monosh_enemy_bullet_count
EXTERN _monosh_player_x
EXTERN _monosh_player_bottom
EXTERN _monosh_enemy_player_hit
EXTERN _monosh_enemy_active_count_value
EXTERN _monosh_enemy_em1_phase
EXTERN _monosh_enemy_em1_shrink
EXTERN _monosh_enemy_collision_cursor
EXTERN _monosh_enemy_path_frames
EXTERN _monosh_enemy_path_fire_frames
EXTERN _monosh_enemy_fire_em1_fast
EXTERN _monosh_enemy_remove_em1_fast
EXTERN _monosh_enemy_em1_count
EXTERN _monosh_enemy_spawn_wait
EXTERN _monosh_enemy_spawn_index
EXTERN _monosh_enemy_spawns
EXTERN _monosh_enemy_stage_complete_flag
EXTERN _monosh_enemy_camera_delta_cached
EXTERN _monosh_runtime_frame_counter
EXTERN _monosh_enemy_geometry
EXTERN _monosh_bom_geometry
EXTERN _monosh_em1_closed_geometry
EXTERN _monosh_em1_open_geometry
EXTERN _monosh_em1_animation_assets_ready
EXTERN _monosh_enemy_ground_bottom
EXTERN _monosh_ebullet_animation_geometry
EXTERN _monosh_ebullet4_geometry
EXTERN _monosh_ebullet_velocity
EXTERN _monosh_ground_screen_delta
EXTERN _monosh_player_bullets
EXTERN _monosh_player_bullet_count
EXTERN _monosh_collision_bullet_bands
EXTERN _monosh_collision_band_bits
EXTERN _monosh_collision_min_x
EXTERN _monosh_collision_max_x
EXTERN _monosh_combat_reflect_bullet
EXTERN _mode3_attribute_count
EXTERN _mode3_depth_reserve
EXTERN _mode3_depth_reserve_clobber
EXTERN _v9968_ground_stripes_pump_preserve_bc
EXTERN _v9968_ground_stripes_pump_clobber

SECTION bss_compiler
enemy_fast_left:    defs 1
enemy_fast_sx:      defs 1
enemy_fast_bottom:  defs 1
enemy_fast_player_vx: defs 1
enemy_fast_width:   defs 1
enemy_fast_height:  defs 1
enemy_fast_asset:   defs 1
enemy_fast_bullet_x: defs 2
enemy_fast_attribute_pointer: defs 2
enemy_fast_bullet_plane_width: defs 1
enemy_fast_bullet_pattern_small: defs 1
enemy_fast_bullet_pattern_left: defs 1
enemy_fast_bullet_pattern_right: defs 1
enemy_fast_bullet_pattern: defs 1
enemy_fast_bullet_page: defs 1
enemy_fast_bullet_shift: defs 1
enemy_fast_bullet_flags: defs 1
enemy_fast_explosion_ground: defs 1
enemy_fast_index: defs 1
enemy_fast_path_pattern: defs 1
enemy_fast_collision_z_biased: defs 1
enemy_fast_collision_z_span: defs 1
enemy_fast_collision_bullet_index: defs 1
enemy_fast_collision_reflector_index: defs 1
; Six five-byte boss-shot interpolation records: X correction/unused,
; Y correction/unused, and the 60 Hz half-step phase.
_monosh_boss_bullet_aim: defs 30

SECTION code_compiler

; H=enemy type, L=path/lane pattern.  Initialise one dense slot directly from
; the generated path head.  This removes the generic C structure/pointer work
; that otherwise forms a visible spike on every formation spawn field.
SECTION CODE_2
_monosh_enemy_fast_add:
    ld a,h
    cp 5
    jr z,enemy_fast_add_type_ready
    cp 6
    ret nz
enemy_fast_add_type_ready:
    ld b,h                         ; type
    ld c,l                         ; pattern
    ld a,(_monosh_enemy_active_count_value)
    cp 8
    ret nc
    push ix
    push iy
    ld l,a
    ld h,0
    ld e,a
    ld d,0
    add hl,hl                      ; 2n
    add hl,hl                      ; 4n
    add hl,de                      ; 5n
    add hl,hl                      ; 10n
    ld de,_monosh_enemies
    add hl,de
    push hl
    pop ix
    ld (ix+0),1
    ld (ix+1),b
    ld (ix+2),c
    xor a
    ld (ix+3),a
    ld (ix+7),a
    ld (ix+8),a
    ld (ix+9),a
    ld a,128
    ld (ix+4),a
    ld a,120
    ld (ix+5),a

    ; Clear parallel EM1 state for the new dense slot.
    ld a,(_monosh_enemy_active_count_value)
    ld e,a
    ld d,0
    ld hl,_monosh_enemy_em1_shrink
    add hl,de
    xor a
    ld (hl),a
    ld l,e
    ld h,0
    add hl,hl
    ld de,_monosh_enemy_em1_phase
    add hl,de
    xor a
    ld (hl),a
    inc hl
    ld (hl),a

    ld a,b
    cp 6
    jr z,enemy_fast_add_em1
    ; MonoshEnemyPath is pointer,frames,fire-frame: four bytes per pattern.
    ld a,c
    add a,a
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_enemy_paths
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,(hl)
    ld (ix+4),a
    inc hl
    ld a,(hl)
    ld e,a
    ld a,(_monosh_ground_screen_delta)
    add a,e
    ld (ix+5),a
    inc hl
    ld a,(hl)
    ld (ix+6),a
    cp 111
    jr c,enemy_fast_add_em0_geometry_z_ready
    ld a,110
enemy_fast_add_em0_geometry_z_ready:
    add a,a
    ld e,a
    ld d,0
    push hl                        ; sample[2]
    ld hl,_monosh_enemy_geometry
    add hl,de
    ld a,(hl)
    ld (ix+8),a
    inc hl
    ld a,(hl)
    ld (ix+9),a
    pop hl
    ; EM0 never mirrors.  Reuse its otherwise dead display byte as the
    ; countdown to the single source firing field.
    ld a,c
    ld e,a
    ld d,0
    ld hl,_monosh_enemy_path_fire_frames
    add hl,de
    ld a,(hl)
    ld (ix+7),a
    jr enemy_fast_add_finish

enemy_fast_add_em1:
    ld (ix+6),110
    ld a,(_monosh_enemy_em1_count)
    inc a
    ld (_monosh_enemy_em1_count),a
enemy_fast_add_finish:
    ld a,(_monosh_enemy_active_count_value)
    inc a
    ld (_monosh_enemy_active_count_value),a
    pop iy
    pop ix
    ret

; Return HL=1 when the current spawn entry is due.  Otherwise consume one
; interpolated 60 Hz wait field and return zero.  This mirrors the NES
; relative timer without paying z88dk's 16-bit struct/compare path every
; field.
SECTION CODE_2
_monosh_enemy_fast_spawn_due:
    ld hl,(_monosh_enemy_spawn_wait)
    ld a,h
    or l
    jr z,enemy_fast_spawn_due_now
    dec hl
    ld (_monosh_enemy_spawn_wait),hl
    ld hl,0
    ret
enemy_fast_spawn_due_now:
    ld hl,1
    ret

; Complete bank-local enemy frame.  The C version routed the common path
; through logic_tick(), enemy_update() and enemy_render(), materialising
; byte tests as 16-bit temporaries between each call.  Keep the identical
; ordering and 30 Hz collision parity while joining the already-assembly hot
; routines directly.
SECTION CODE_2
_monosh_enemy_frame:
    ld a,(_monosh_enemy_stage_complete_flag)
    or a
    jr z,enemy_fast_frame_general
    ld a,(_monosh_enemy_active_count_value)
    or a
    jr nz,enemy_fast_frame_general
    ld a,(_monosh_enemy_bullet_count)
    or a
    call nz,_monosh_enemy_fast_update_bullets
    jp enemy_fast_frame_render

enemy_fast_frame_general:
    ld a,(_monosh_enemy_em1_count)
    or a
    call nz,_monosh_enemy_fast_update_em1
    call _monosh_enemy_fast_advance
    ld a,(_monosh_enemy_bullet_count)
    or a
    call nz,_monosh_enemy_fast_update_bullets

    ld a,(_monosh_player_bullet_count)
    or a
    jr z,enemy_fast_frame_spawn_check
    ld a,(_monosh_enemy_active_count_value)
    or a
    jr z,enemy_fast_frame_spawn_check
    ld a,(_monosh_runtime_frame_counter)
    rra
    call nc,_monosh_enemy_fast_check_player_bullets

enemy_fast_frame_spawn_check:
    ld a,(_monosh_enemy_stage_complete_flag)
    or a
    jr nz,enemy_fast_frame_render
    call _monosh_enemy_fast_spawn_due
    ld a,h
    or l
    jr z,enemy_fast_frame_render
    ld b,32

enemy_fast_frame_spawn_loop:
    ld a,(_monosh_enemy_spawn_index)
    add a,a
    add a,a
    ld l,a
    ld h,0
    ld de,_monosh_enemy_spawns
    add hl,de
    inc hl
    inc hl
    ld a,(hl)                       ; type
    cp $ff
    jr z,enemy_fast_frame_spawn_end
    ld d,a
    inc hl
    ld e,(hl)                       ; pattern
    ld a,d
    cp $fe
    jr z,enemy_fast_frame_spawn_advance
    push bc
    ld h,d
    ld l,e
    call _monosh_enemy_fast_add
    pop bc

enemy_fast_frame_spawn_advance:
    ld a,(_monosh_enemy_spawn_index)
    inc a
    ld (_monosh_enemy_spawn_index),a
    add a,a
    add a,a
    ld l,a
    ld h,0
    ld de,_monosh_enemy_spawns
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld (_monosh_enemy_spawn_wait),hl
    call _monosh_enemy_fast_spawn_due
    ld a,h
    or l
    jr z,enemy_fast_frame_render
    djnz enemy_fast_frame_spawn_loop
    jr enemy_fast_frame_render

enemy_fast_frame_spawn_end:
    ld hl,0
    ld (_monosh_enemy_spawn_wait),hl
    inc l
    ld a,l
    ld (_monosh_enemy_stage_complete_flag),a

enemy_fast_frame_render:
    ld a,(_monosh_ground_screen_delta)
    ld (_monosh_enemy_camera_delta_cached),a
    ld a,(_monosh_enemy_bullet_count)
    or a
    call nz,_monosh_enemy_fast_render_bullets
    ld a,(_monosh_enemy_active_count_value)
    or a
    call nz,_monosh_enemy_fast_render
    ld a,(_monosh_enemy_player_hit)
    ld l,a
    ld h,0
    xor a
    ld (_monosh_enemy_player_hit),a
    ret

SECTION CODE_2

; HL=current ten-byte EM0 slot.  Append one normal projectile to the dense
; seven-byte pool and reproduce fire_enemy_bullet_variant()'s exact aim:
; player VBUF X = screenX/2+60, quarter-pixel distance lookup, then rounded
; half velocity for the doubled 60 Hz timeline.  Keeping the complete path
; in bank 2 removes the C pointer/arithmetic spike when a dense formation
; fires on adjacent fields.
_monosh_enemy_fire_em0_fast:
    ld a,(_monosh_enemy_bullet_count)
    cp 6
    ret nc
    push hl
    ld l,a
    ld h,0
    ld e,a
    ld d,0
    add hl,hl                       ; 2n
    add hl,hl                       ; 4n
    add hl,hl                       ; 8n
    or a
    sbc hl,de                       ; 7n
    ld de,_monosh_enemy_bullets
    add hl,de
    push hl
    pop ix
    pop hl
    ld de,4
    add hl,de
    ld a,(hl)                       ; source X
    ld (ix+1),a
    inc hl
    ld a,(hl)                       ; source bottom
    ld (ix+2),a
    inc hl
    ld a,(hl)                       ; logical Z
    cp 8
    ret c
    ld (ix+3),a

    ld hl,(_monosh_player_x)
    sra h
    rr l
    ld a,l
    add a,60
    ld e,a                          ; target VBUF X
    ld a,(ix+1)
    cp e
    jr c,enemy_fast_fire_x_positive
    jr z,enemy_fast_fire_x_zero
    sub e
    srl a
    srl a
    ld e,a
    ld a,(ix+3)
    call enemy_fast_fire_velocity
    inc a
    srl a
    neg
    ld (ix+4),a
    jr enemy_fast_fire_y
enemy_fast_fire_x_positive:
    ld a,e
    sub (ix+1)
    srl a
    srl a
    ld e,a
    ld a,(ix+3)
    call enemy_fast_fire_velocity
    inc a
    srl a
    ld (ix+4),a
    jr enemy_fast_fire_y
enemy_fast_fire_x_zero:
    xor a
    ld (ix+4),a

enemy_fast_fire_y:
    ld hl,(_monosh_player_bottom)
    ld a,h
    or a
    jr nz,enemy_fast_fire_y_positive
    ld a,l
    cp (ix+2)
    jr c,enemy_fast_fire_y_negative
enemy_fast_fire_y_positive:
    ld a,l
    sub (ix+2)
    srl a
    srl a
    ld e,a
    ld a,(ix+3)
    call enemy_fast_fire_velocity
    inc a
    srl a
    ld (ix+5),a
    jr enemy_fast_fire_store
enemy_fast_fire_y_negative:
    ld a,(ix+2)
    sub l
    srl a
    srl a
    ld e,a
    ld a,(ix+3)
    call enemy_fast_fire_velocity
    inc a
    srl a
    neg
    ld (ix+5),a
enemy_fast_fire_store:
    xor a
    ld (ix+6),a                    ; normal animation, frame zero
    inc a
    ld (ix+0),a
    ld a,(_monosh_enemy_bullet_count)
    inc a
    ld (_monosh_enemy_bullet_count),a
    ret

; A=logical Z, E=quarter-pixel distance (0..63), returns the source 30 Hz
; velocity in A from the existing 52x64 ROM table.
enemy_fast_fire_velocity:
    srl a
    sub 4
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld d,0
    add hl,de
    ld de,_monosh_ebullet_velocity
    add hl,de
    ld a,(hl)
    ret

SECTION CODE_2

; Advance interpolated EM0 paths and BOM lifetimes at 60 Hz.  EM1 owns a
; separate state machine and is deliberately skipped here.
_monosh_enemy_fast_advance:
    push ix
    push iy
    ld a,$ff
    ld (enemy_fast_path_pattern),a
    ld ix,_monosh_enemies
    ld a,(_monosh_enemy_active_count_value)
    or a
    jp z,enemy_fast_advance_done
    ld b,a
enemy_fast_advance_loop:
    ; Slots 0..active_count-1 are dense.  Removed entries are replaced by
    ; the former last slot, so the active-byte test in every hot iteration
    ; was redundant.
    ld a,(ix+1)
    cp 2
    jp z,enemy_fast_advance_bom
    cp 5
    jp nz,enemy_fast_advance_next
    ; display is unused by EM0 (these bodies are never mirrored), so it holds
    ; a one-shot fire countdown prepared at spawn.  This removes two indexed
    ; ROM-table address calculations from every live body on every field.
    ld a,(ix+3)
    inc a
    ld c,a
    ld a,(ix+7)
    or a
    jr nz,enemy_fast_advance_no_fire
    jr enemy_fast_advance_fire_done
enemy_fast_advance_no_fire:
    dec a
    ld (ix+7),a
    jr nz,enemy_fast_advance_fire_done
    push bc
    push ix
    push ix
    pop hl
    call _monosh_enemy_fire_em0_fast
    pop ix
    pop bc
    ; A banked/C side effect may use IY.  Match the source updater and force
    ; the path pointer cache to reload after the rare firing call.
    ld a,$ff
    ld (enemy_fast_path_pattern),a
enemy_fast_advance_fire_done:
    ld a,c
    ld (ix+3),a
    ; Four path lengths cover all nine closed patterns.  Comparing their
    ; ranges is cheaper than forming a ROM pointer for a nine-byte table.
    ld a,(ix+2)
    or a
    jr z,enemy_fast_advance_limit_245
    cp 4
    jr c,enemy_fast_advance_limit_235
    cp 6
    jr c,enemy_fast_advance_limit_239
    ld a,c
    cp 189
    jr enemy_fast_advance_limit_ready
enemy_fast_advance_limit_245:
    ld a,c
    cp 245
    jr enemy_fast_advance_limit_ready
enemy_fast_advance_limit_235:
    ld a,c
    cp 235
    jr enemy_fast_advance_limit_ready
enemy_fast_advance_limit_239:
    ld a,c
    cp 239
enemy_fast_advance_limit_ready:
    jp nc,enemy_fast_advance_remove
    ; The old path made a second complete eight-slot pass to refresh EM0
    ; geometry.  The active slot is already in IX here, so consume its path
    ; sample before advancing to the next slot.
    ; This geometry worker has a single hot caller.  Tail-enter it so every
    ; live EM0 avoids a CALL/RET pair; it jumps back after caching sx/Y/Z and
    ; the exact interpolated width/height.
    jp enemy_fast_geometry_current
enemy_fast_geometry_current_done:

    ; The NES body-contact path tests EM0 only when its displayed depth has
    ; reached exactly zero.  Enemy X remains in the source half-resolution
    ; VBUF coordinate system.  Source player_vbuf_x is 124 + source playerX/2;
    ; MSX player X is source playerX + 128, hence screenX/2 + 60.  Using +64
    ; shifted contact eight screen pixels right and changed distant hits.
    ; retain the original asymmetric [-14,+21] horizontal interval.  Y is
    ; already a full-resolution bottom coordinate and retains [-20,+32].
    ld a,(ix+6)
    or a
    jp nz,enemy_fast_advance_next
    ld hl,(_monosh_player_x)
    sra h
    rr l
    ld a,l
    add a,60
    ld e,a
    ld a,(ix+4)
    sub e
    add a,14
    cp 36
    jp nc,enemy_fast_advance_next
    ld a,(ix+5)
    ld e,a
    ld a,(_monosh_player_bottom)
    ld d,a
    ld a,e
    sub d
    add a,20
    cp 53
    jp nc,enemy_fast_advance_next
    ld a,1
    ld (_monosh_enemy_player_hit),a
    jp enemy_fast_advance_next
enemy_fast_advance_bom:
    ld a,(ix+3)
    or a
    jp z,enemy_fast_advance_remove
    dec a
    ld (ix+3),a
    jp z,enemy_fast_advance_remove
    ; z=55 is far and z=0 is at the camera.  Grow toward the foreground and
    ; land an airborne kill over six ticks.  Once landed, follow the
    ; depth-dependent ground projection.
    ld a,(ix+6)
    cp 2
    jp c,enemy_fast_advance_remove
    dec a
    ld (ix+6),a
enemy_fast_advance_bom_ground:
    ld a,(ix+6)
    ld e,a
    ld d,0
    ld hl,_monosh_enemy_ground_bottom
    add hl,de
    ld a,(hl)
    ld e,a
    ld a,(_monosh_ground_screen_delta)
    add a,e
    ld (enemy_fast_explosion_ground),a
    ld a,(ix+7)
    or a
    jr z,enemy_fast_advance_bom_snap_ground
    ld d,a
    ld a,(enemy_fast_explosion_ground)
    sub (ix+5)
    jr c,enemy_fast_advance_bom_snap_ground
    jr z,enemy_fast_advance_bom_landed
    ; 60 Hz ballistic fall: speed rises from 1 to 12 pixels/field.  The old
    ; ceil(distance/remaining) loop could execute dozens of subtractions for
    ; every explosion and was the dominant cost immediately after a hit.
    ld a,13
    sub d
    ld e,a
    ld a,(ix+5)
    add a,e
    ld d,a
    ld a,(enemy_fast_explosion_ground)
    cp d
    jr nc,enemy_fast_advance_bom_store_fall
    ld d,a
enemy_fast_advance_bom_store_fall:
    ld (ix+5),d
    dec (ix+7)
    jr enemy_fast_advance_bom_size
enemy_fast_advance_bom_snap_ground:
    ld a,(enemy_fast_explosion_ground)
    ld (ix+5),a
enemy_fast_advance_bom_landed:
    xor a
    ld (ix+7),a
enemy_fast_advance_bom_size:
    ld a,(ix+6)
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_bom_geometry
    add hl,de
    ld a,(hl)
    ld (ix+8),a
    inc hl
    ld a,(hl)
    ld (ix+9),a
    jp enemy_fast_advance_next
enemy_fast_advance_remove:
    ; The dense slot index is needed only on the rare removal path to move the
    ; parallel EM1 lanes.  Derive it here from IX instead of maintaining a BSS
    ; index with a load/increment/store on every live enemy every field.
    push ix
    pop hl
    ld de,_monosh_enemies
    or a
    sbc hl,de
    ld c,0
enemy_fast_advance_remove_index_loop:
    ld a,l
    or a
    jr z,enemy_fast_advance_remove_index_ready
    sub 10
    ld l,a
    inc c
    jr enemy_fast_advance_remove_index_loop
enemy_fast_advance_remove_index_ready:
    ld a,c
    ld (enemy_fast_index),a
    ld a,(_monosh_enemy_active_count_value)
    dec a
    ld (_monosh_enemy_active_count_value),a
    ; Dense active array: replace the removed slot with the former last one.
    ; Removal is rare, so copying ten bytes here is far cheaper than scanning
    ; eight sparse slots in both hot loops on every 60 Hz field.
    ld l,a
    ld h,0
    ld e,l
    ld d,0
    add hl,hl
    add hl,hl
    add hl,de
    add hl,hl                    ; last index * 10
    ld de,_monosh_enemies
    add hl,de                    ; HL = former last slot
    push hl
    push ix
    pop de
    or a
    sbc hl,de
    pop hl
    jr z,enemy_fast_advance_remove_last
    push bc
    push hl
    push ix
    pop de
    ld bc,10
    ldir
    ; EM1 phase is a parallel 16-bit SoA lane; move it with the dense slot.
    ld a,(_monosh_enemy_active_count_value)
    add a,a
    ld l,a
    ld h,0
    ld de,_monosh_enemy_em1_phase
    add hl,de
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld a,(enemy_fast_index)
    add a,a
    ld l,a
    ld h,0
    add hl,de
    ld (hl),c
    inc hl
    ld (hl),b
    ; Move the source-style EM1 shrink accumulator with the dense slot.
    ld a,(_monosh_enemy_active_count_value)
    ld l,a
    ld h,0
    ld de,_monosh_enemy_em1_shrink
    add hl,de
    ld c,(hl)
    ld a,(enemy_fast_index)
    ld l,a
    ld h,0
    add hl,de
    ld (hl),c
    pop hl
    xor a
    ld (hl),a                    ; clear the former last slot
    pop bc
    jr enemy_fast_advance_remove_cursor
enemy_fast_advance_remove_last:
    xor a
    ld (ix+0),a
enemy_fast_advance_remove_cursor:
    dec b
    jp nz,enemy_fast_advance_loop
    jr enemy_fast_advance_done
enemy_fast_advance_next:
    ld de,10
    add ix,de
    dec b
    jp nz,enemy_fast_advance_loop
enemy_fast_advance_done:
    pop iy
    pop ix
    ret

; Cache the current sx,bottom,wz triplet for the EM0 slot already selected by
; the advance loop.  Non-player objects are never mirrored, so no direction
; comparison against the following path sample is needed.
enemy_fast_geometry_current:
    ld a,(ix+2)
    ld e,a
    ld a,(enemy_fast_path_pattern)
    cp e
    jr z,enemy_fast_geometry_path_ready
    ld a,e
    ld (enemy_fast_path_pattern),a
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld de,_monosh_enemy_paths
    add hl,de
    push hl
    pop iy

enemy_fast_geometry_path_ready:

    ld c,(ix+3)
    ld l,(iy+0)
    ld h,(iy+1)
    ld e,c
    ld d,0
    add hl,de
    add hl,de
    add hl,de
    ld a,(hl)
    ld (ix+4),a
    inc hl
    ld a,(hl)
    ld e,a
    ld a,(_monosh_ground_screen_delta)
    add a,e
    ld (ix+5),a
    inc hl
    ld a,(hl)
    ld (ix+6),a
enemy_fast_geometry_size:
    ld a,(ix+6)
    cp 111
    jr c,enemy_fast_geometry_depth_ready
    ld a,110
enemy_fast_geometry_depth_ready:
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_enemy_geometry
    add hl,de
    ld a,(hl)
    ld (ix+8),a
    inc hl
    ld a,(hl)
    ld (ix+9),a
    jp enemy_fast_geometry_current_done

; Advance the six enemy bullets and perform their compact player hit test.
; This is the same 60 Hz state transition as the C reference, without signed
; 16-bit arithmetic in the inner loop.
; Every caller is in monosh_enemy.c (bank 2), so this hot path need not occupy
; the fixed 16 KiB cartridge window.
SECTION CODE_2
_monosh_enemy_fast_update_bullets:
    push ix
    push iy
    ld hl,(_monosh_player_x)
    sra h
    rr l
    ld a,l
    ; Match source player_vbuf_x = 124 + source playerX/2.  The MSX absolute
    ; player centre is source playerX + 128, so its VBUF bias is 60.
    add a,60
    ld (enemy_fast_player_vx),a
    ld ix,_monosh_enemy_bullets
    ld iy,_monosh_boss_bullet_aim
    ld a,(_monosh_enemy_bullet_count)
    or a
    jp z,enemy_fast_update_bullet_done
    ld (enemy_fast_left),a
enemy_fast_update_bullet_loop:
    ; Normal shots advance one 64-field rotation age every field.  The two
    ; high bits are unused; boss shots carry bit 7 and remain unanimated.
    ld a,(ix+6)
    bit 7,a
    jr nz,enemy_fast_update_bullet_depth_select
    inc a
    and 63
    ld (ix+6),a
enemy_fast_update_bullet_depth_select:
    ld a,(ix+3)
    or a
    jr nz,enemy_fast_update_bullet_depth
    ld a,(ix+0)
    cp 2
    jp z,enemy_fast_update_bullet_remove
    ; A source projectile receives Z+1 movement updates.  Doubled MSX depth
    ; normally supplies two fields per source update, but an even Z2 reaches
    ; the front after the first half of its final pair.  Keep a boss shot in
    ; state 1 for that one extra half-step; normal shots retain their existing
    ; front-ready timing.
    ld a,(ix+6)
    bit 7,a
    jr z,enemy_fast_update_bullet_mark_front
    ld a,(iy+4)
    and 1
    jr z,enemy_fast_update_bullet_move
enemy_fast_update_bullet_mark_front:
    ld (ix+0),2
    jr enemy_fast_update_bullet_move
enemy_fast_update_bullet_depth:
    dec (ix+3)
enemy_fast_update_bullet_move:
    ld a,(ix+4)
    add a,(ix+1)
    ld (ix+1),a
    ld a,(ix+5)
    add a,(ix+2)
    ld (ix+2),a
    ld a,(ix+6)
    bit 7,a
    call nz,enemy_fast_update_bullet_dda
    ld a,(ix+2)
    cp 224
    jr nc,enemy_fast_update_bullet_remove
    ld a,(ix+0)
    cp 2
    jp nz,enemy_fast_update_bullet_next
    ld a,(ix+3)
    or a
    jp nz,enemy_fast_update_bullet_next

    ; (x - player_x) in [-10,17] iff its biased unsigned value is < 28.
    ld a,(ix+1)
    ld e,a
    ld a,(enemy_fast_player_vx)
    ld d,a
    ld a,e
    sub d
    add a,10
    cp 28
    jr nc,enemy_fast_update_bullet_next
    ; (y - player_bottom) in [-20,40] iff biased value is < 61.
    ld a,(ix+2)
    ld e,a
    ld a,(_monosh_player_bottom)
    ld d,a
    ld a,e
    sub d
    add a,20
    cp 61
    jr nc,enemy_fast_update_bullet_next
    ld a,1
    ld (_monosh_enemy_player_hit),a
    jr enemy_fast_update_bullet_next

enemy_fast_update_bullet_remove:
    ld a,(_monosh_enemy_bullet_count)
    dec a
    ld (_monosh_enemy_bullet_count),a
    ; Ascending dense traversal: when more than this slot remains, replace it
    ; with the former last projectile and process that replacement here.
    ld a,(enemy_fast_left)
    cp 1
    jr z,enemy_fast_update_bullet_removed_last
    ld a,(_monosh_enemy_bullet_count)
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    or a
    sbc hl,de                       ; last index * 7
    ld de,_monosh_enemy_bullets
    add hl,de
    push ix
    pop de
    ld bc,7
    ldir
    ; Keep the inactive tail canonical for diagnostics and the rare C-side
    ; reset paths, even though hot update/render loops stop at dense count.
    ld de,-7
    add hl,de
    xor a
    ld (hl),a

    ld a,(_monosh_enemy_bullet_count)
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,de                       ; last index * 5
    ld de,_monosh_boss_bullet_aim
    add hl,de
    push iy
    pop de
    ld bc,5
    ldir
    jr enemy_fast_update_bullet_removed_finish
enemy_fast_update_bullet_removed_last:
    xor a
    ld (ix+0),a
enemy_fast_update_bullet_removed_finish:
    ld a,(enemy_fast_left)
    dec a
    ld (enemy_fast_left),a
    jp z,enemy_fast_update_bullet_done
    jp enemy_fast_update_bullet_loop
enemy_fast_update_bullet_next:
    ld de,7
    add ix,de
    ld de,5
    add iy,de
    ld a,(enemy_fast_left)
    dec a
    ld (enemy_fast_left),a
    jp nz,enemy_fast_update_bullet_loop
enemy_fast_update_bullet_done:
    pop iy
    pop ix
    ret

; Player-shot collision against cached EM0/EM1 geometry.  The former C path
; performed signed 16-bit arithmetic inside a 3x8 nested loop while firing.
SECTION code_compiler
_monosh_enemy_fast_check_player_bullets:
    push ix
    push iy
    ; Walk the complete dense target array in one assembly entry.  This avoids
    ; a bank-local C call plus IX/IY save/restore for each of up to eight
    ; enemies, while all three shots reuse each target's rectangle.
    ld a,(_monosh_enemy_active_count_value)
    or a
    jp z,enemy_fast_collision_done
    ld b,a
    xor a
    ld (enemy_fast_collision_reflector_index),a
    ld iy,_monosh_enemies
enemy_fast_collision_target_loop:
    ; B is needed for a shot's Y coordinate below.  Preserve the dense target
    ; count on the stack and retain IY as the live target cursor instead of
    ; reloading/updating a BSS pointer and counter for every enemy.
    push bc
    ; Geometry belongs to the selected enemy, not to a projectile.  The old
    ; split MSX path rebuilt the same EM1 table lookup, ground adjustment and
    ; reflect state up to three times here (once for each live player shot).
    ; The NES path obtains these values once from the enemy update cache.
    ; Hoist the invariant work before the projectile loop while retaining the
    ; existing one-selected-enemy cadence and exact hit intervals.
    ; active_count describes a compact prefix.  Removal immediately replaces
    ; a hole with the former last record, so every slot visited here is active.
    ; Do not re-read/test the redundant active byte in this per-enemy hot path.
    ; Reject an empty common Z band before rebuilding any target geometry.
    ; The same eight-band mask is consumed by the Stage renderer.
    ld a,(iy+6)
    rrca
    rrca
    rrca
    rrca
    and 7
    ld e,a
    ld d,0
    ld hl,_monosh_collision_band_bits
    add hl,de
    ld a,(_monosh_collision_bullet_bands)
    and (hl)
    or a
    jp z,enemy_fast_collision_target_next

    ld a,(iy+1)
    cp 5
    jr z,enemy_fast_collision_prepare_em0
    cp 6
    jp nz,enemy_fast_collision_target_next
    ld a,(iy+7)
    bit 7,a
    jr z,enemy_fast_collision_prepare_em1_closed
    ld a,(iy+6)
    ld (enemy_fast_asset),a       ; raw Z during this routine
    cp 80
    jr nc,enemy_fast_collision_prepare_em1_far
    cp 54
    jr nc,enemy_fast_collision_prepare_em1_mid
    ld e,14
    jr enemy_fast_collision_prepare_em1_index_ready
enemy_fast_collision_prepare_em1_far:
    ld e,4
    jr enemy_fast_collision_prepare_em1_index_ready
enemy_fast_collision_prepare_em1_mid:
    ld e,9
enemy_fast_collision_prepare_em1_index_ready:
    sla e
    ld d,0
    ld hl,_monosh_em1_open_geometry
    add hl,de
    jr enemy_fast_collision_prepare_em1_store_geometry

enemy_fast_collision_prepare_em1_closed:
    ld a,(iy+6)
    ld (enemy_fast_asset),a
    cp 111
    jr c,enemy_fast_collision_prepare_em1_closed_z_ready
    ld a,110
enemy_fast_collision_prepare_em1_closed_z_ready:
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_em1_closed_geometry
    add hl,de
enemy_fast_collision_prepare_em1_store_geometry:
    ld a,(hl)
    ld (enemy_fast_width),a
    inc hl
    ld a,(hl)
    ld (enemy_fast_height),a
enemy_fast_collision_prepare_em1_bottom:
    ld a,(iy+5)
    ld e,a
    ld a,(_monosh_ground_screen_delta)
    add a,e
    ld (enemy_fast_bottom),a
    jr enemy_fast_collision_target_ready

enemy_fast_collision_prepare_em0:
    ld a,(iy+6)
    ld (enemy_fast_asset),a
    ld a,(iy+8)
    ld (enemy_fast_width),a
    ld a,(iy+9)
    ld (enemy_fast_height),a
    ld a,(iy+5)
    ld (enemy_fast_bottom),a

enemy_fast_collision_target_ready:
    ; The selected target is invariant for all three projectile slots.  Cache
    ; its projected centre and expanded hit radii once, as the source enemy
    ; loop does, instead of rebuilding them for every live shot.
    ld a,(iy+4)
    cp 64
    jp c,enemy_fast_collision_target_next
    cp 192
    jp nc,enemy_fast_collision_target_next
    sub 64
    add a,a
    ld (enemy_fast_sx),a
    ; A shot is a point, as in NES check_collision.s. Geometry is already
    ; in screen pixels; do not add a fixed projectile radius.
    ld a,(enemy_fast_width)
    srl a
    ld (enemy_fast_width),a
    ; NES source-Z sweep [max(0,bz-4),bz], converted to Z2 including
    ; the interpolated half-step: targetZ2 - 2*bz in [-8,1].
    ld a,(enemy_fast_asset)
    add a,8
    ld (enemy_fast_collision_z_biased),a
    ld a,10
    ld (enemy_fast_collision_z_span),a
    ld a,(iy+1)
    cp 6
    jr nz,enemy_fast_collision_geometry_ready
    bit 7,(iy+7)
    jr nz,enemy_fast_collision_geometry_ready
    ; Closed EM1 alone retains the NES reflection allowance: +/-24 in
    ; source Z4 (=12 in Z2), minimum half-width 10 VBUF pixels (=20 screen),
    ; and minimum full height 24 screen pixels.
    ld a,(enemy_fast_collision_z_biased)
    add a,12
    ld (enemy_fast_collision_z_biased),a
    ld a,34
    ld (enemy_fast_collision_z_span),a
    ld a,(enemy_fast_width)
    cp 20
    jr nc,enemy_fast_collision_closed_width_ready
    ld a,20
    ld (enemy_fast_width),a
enemy_fast_collision_closed_width_ready:
    ld a,(enemy_fast_height)
    cp 24
    jr nc,enemy_fast_collision_geometry_ready
    ld a,24
    ld (enemy_fast_height),a
enemy_fast_collision_geometry_ready:
    ld a,(enemy_fast_height)
    ld e,a
    ld a,(enemy_fast_bottom)
    cp e
    jp c,enemy_fast_collision_target_next

    ; Expand the complete live-shot envelope by this target's radius.  This
    ; is only a broad reject; exact per-shot X/Z/Y checks remain unchanged.
    ld a,(enemy_fast_width)
    ld e,a
    ld a,(_monosh_collision_min_x)
    sub e
    jr nc,enemy_fast_collision_envelope_left_ready
    xor a
enemy_fast_collision_envelope_left_ready:
    ld e,a
    ld a,(enemy_fast_sx)
    cp e
    jp c,enemy_fast_collision_target_next
    ld a,(enemy_fast_width)
    ld e,a
    ld a,(_monosh_collision_max_x)
    add a,e
    jr c,enemy_fast_collision_envelope_right_pass
    ld e,a
    ld a,(enemy_fast_sx)
    cp e
    jp z,enemy_fast_collision_envelope_right_pass
    jp nc,enemy_fast_collision_target_next
enemy_fast_collision_envelope_right_pass:
    ; The player-shot pool is exactly three fixed records.  Load their X/Y/Z
    ; directly into registers instead of paying IX displacement and pointer
    ; loop costs for every enemy.  B=Y, C=X, D=source Z.
    ld a,(_monosh_player_bullets+0)
    cp 1
    jr nz,enemy_fast_collision_slot1
    ld a,(_monosh_player_bullets+2)
    ld b,a
    ld a,(_monosh_player_bullets+1)
    ld c,a
    ld a,(_monosh_player_bullets+3)
    ld d,a
    ; Inline the first two probes.  A dense held-fire field tests these for
    ; every candidate enemy, so avoiding sixteen CALL/RET pairs removes a
    ; collision spike without changing any interval or traversal order.
    ld a,(enemy_fast_sx)
    ld e,a
    ld a,c
    cp e
    jr nc,enemy_fast_collision_x0_shot_right
    ld a,e
    sub c
    jr enemy_fast_collision_x0_distance_ready
enemy_fast_collision_x0_shot_right:
    sub e
enemy_fast_collision_x0_distance_ready:
    ld l,a
    ld a,(enemy_fast_width)
    cp l
    jr c,enemy_fast_collision_slot1
    ld a,d
    add a,a
    ld e,a
    ld a,(enemy_fast_collision_z_biased)
    sub e
    ld l,a
    ld a,(enemy_fast_collision_z_span)
    cp l
    jr z,enemy_fast_collision_slot1
    jr c,enemy_fast_collision_slot1
    ; Y is [bottom-height,bottom], not a radius around the bottom.
    ld a,(enemy_fast_bottom)
    sub b
    jr c,enemy_fast_collision_slot1
    ld l,a
    ld a,(enemy_fast_height)
    cp l
    jr nc,enemy_fast_collision_hit0
enemy_fast_collision_slot1:
    ld a,(_monosh_player_bullets+5)
    cp 1
    jr nz,enemy_fast_collision_slot2
    ld a,(_monosh_player_bullets+7)
    ld b,a
    ld a,(_monosh_player_bullets+6)
    ld c,a
    ld a,(_monosh_player_bullets+8)
    ld d,a
    ld a,(enemy_fast_sx)
    ld e,a
    ld a,c
    cp e
    jr nc,enemy_fast_collision_x1_shot_right
    ld a,e
    sub c
    jr enemy_fast_collision_x1_distance_ready
enemy_fast_collision_x1_shot_right:
    sub e
enemy_fast_collision_x1_distance_ready:
    ld l,a
    ld a,(enemy_fast_width)
    cp l
    jr c,enemy_fast_collision_slot2
    ld a,d
    add a,a
    ld e,a
    ld a,(enemy_fast_collision_z_biased)
    sub e
    ld l,a
    ld a,(enemy_fast_collision_z_span)
    cp l
    jr z,enemy_fast_collision_slot2
    jr c,enemy_fast_collision_slot2
    ; Y is [bottom-height,bottom], not a radius around the bottom.
    ld a,(enemy_fast_bottom)
    sub b
    jr c,enemy_fast_collision_slot2
    ld l,a
    ld a,(enemy_fast_height)
    cp l
    jr nc,enemy_fast_collision_hit1
enemy_fast_collision_slot2:
    ld a,(_monosh_player_bullets+10)
    cp 1
    jp nz,enemy_fast_collision_target_next
    ld a,(_monosh_player_bullets+12)
    ld b,a
    ld a,(_monosh_player_bullets+11)
    ld c,a
    ld a,(_monosh_player_bullets+13)
    ld d,a
    jp enemy_fast_collision_values_slot2
enemy_fast_collision_hit2:
    ld ix,_monosh_player_bullets+10
    ld a,2
    jr enemy_fast_collision_hit_ready
enemy_fast_collision_hit0:
    ld ix,_monosh_player_bullets
    xor a
    jr enemy_fast_collision_hit_ready
enemy_fast_collision_hit1:
    ld ix,_monosh_player_bullets+5
    ld a,1
enemy_fast_collision_hit_ready:
    ld (enemy_fast_collision_bullet_index),a
    jr enemy_fast_collision_resolve

; Tail probe for slot 2.  B=shot Y, C=shot X, D=source Z.  The first two
; probes are inlined above; this final one can jump directly to hit/miss and
; likewise needs no CALL/RET pair in the per-target loop.
enemy_fast_collision_values_slot2:
    ld a,(enemy_fast_sx)
    ld e,a
    ld a,c
    cp e
    jr nc,enemy_fast_collision_x_shot_right
    ld a,e
    sub c
    jr enemy_fast_collision_x_distance_ready
enemy_fast_collision_x_shot_right:
    sub e
enemy_fast_collision_x_distance_ready:
    ld l,a
    ld a,(enemy_fast_width)
    cp l
    jp c,enemy_fast_collision_target_next
    ; Formations spread widely in X while all members traverse similar Z.
    ; Reject the cheap cached screen interval before paying exact source-Z.
    ld a,d
    add a,a
    ld e,a
    ld a,(enemy_fast_collision_z_biased)
    sub e
    ld l,a
    ld a,(enemy_fast_collision_z_span)
    cp l
    jp z,enemy_fast_collision_target_next
    jp c,enemy_fast_collision_target_next
    ; Y is [bottom-height,bottom], not a radius around the bottom.
    ld a,(enemy_fast_bottom)
    sub b
    jp c,enemy_fast_collision_target_next
    ld l,a
    ld a,(enemy_fast_height)
    cp l
    jp c,enemy_fast_collision_target_next
    jp enemy_fast_collision_hit2

enemy_fast_collision_resolve:
    ; Reflection is wholly encoded by the current target: only a closed EM1
    ; (type 6 with display bit 7 clear) reflects.  Re-evaluate this rare hit
    ; instead of storing the same flag for every scanned target.
    ld a,(iy+1)
    cp 6
    jr nz,enemy_fast_collision_destroy
    bit 7,(iy+7)
    jr nz,enemy_fast_collision_destroy
    ; The reflected shot moves into the independent three-slot pool.  This
    ; preserves the normal firing capacity while it flies to a screen edge.
    push bc
    push ix
    push iy
    ld a,(enemy_fast_collision_bullet_index)
    ld l,a
    ld a,(enemy_fast_collision_reflector_index)
    ld h,a
    call _monosh_combat_reflect_bullet
    pop iy
    pop ix
    pop bc
    jp enemy_fast_collision_target_next

enemy_fast_collision_destroy:
    xor a
    ld (ix+0),a
    ld a,(_monosh_player_bullet_count)
    dec a
    ld (_monosh_player_bullet_count),a
    ld (iy+3),48
    ld a,(enemy_fast_bottom)
    ld (iy+5),a
    ld a,(enemy_fast_asset)
    ld (iy+6),a
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_bom_geometry
    add hl,de
    ld a,(hl)
    ld (iy+2),a
    ld (iy+8),a
    inc hl
    ld a,(hl)
    ld (iy+9),a
    ld (iy+7),12
    ld a,(iy+1)
    cp 6
    jr nz,enemy_fast_collision_hit_type_ready
    ld a,(_monosh_enemy_em1_count)
    dec a
    ld (_monosh_enemy_em1_count),a
enemy_fast_collision_hit_type_ready:
    ld (iy+1),2
    ; The selected target is now an explosion.  Continue with the next dense
    ; target; the consumed projectile is rejected by its active byte.
    jp enemy_fast_collision_target_next
enemy_fast_collision_target_next:
    ld a,(_monosh_player_bullet_count)
    or a
    jr z,enemy_fast_collision_done_pop_count
    pop bc
    ld de,10
    add iy,de
    ld a,(enemy_fast_collision_reflector_index)
    inc a
    ld (enemy_fast_collision_reflector_index),a
    dec b
    jp nz,enemy_fast_collision_target_loop
    jr enemy_fast_collision_done
enemy_fast_collision_done_pop_count:
    pop bc
enemy_fast_collision_done:
    pop iy
    pop ix
    ret

; Convert virtual-buffer X to signed screen centre X in HL.
enemy_fast_center_x:
    sub 64
    ld l,a
    ld h,0
    bit 7,l
    jr z,enemy_fast_center_ready
    dec h
enemy_fast_center_ready:
    add hl,hl
    ret

; Emit one enemy body directly into the V9968 attribute stream.  The active
; enemy assets all use SZ=0 for their 16-pixel source and SZ=1 for their
; 32-pixel source, so no generic draw-command decode is required.
enemy_fast_queue:
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_asset)
    cp 3
    jr z,enemy_fast_body_patterns_em0
    cp 5
    jr z,enemy_fast_body_patterns_bom
    cp 11
    jr z,enemy_fast_body_patterns_em1_closed
    ; EM1 open poses are assets 32..36, three consecutive patterns each.
    sub 32
    ld e,a
    add a,a
    add a,e
    ; V9968 SCREEN 5 page 3 is the bitmap back buffer, so the extended EM1
    ; animation patterns live in mode-3 sprite page 3 (VRAM 0x20000).
    ld e,3
    jr enemy_fast_body_patterns_ready
enemy_fast_body_patterns_em0:
    ld a,$0b
    ld e,0
    jr enemy_fast_body_patterns_ready
enemy_fast_body_patterns_bom:
    call enemy_fast_select_bom_patterns
    jr enemy_fast_body_patterns_ready
enemy_fast_body_patterns_em1_closed:
    xor a
    ld e,1
enemy_fast_body_patterns_ready:
    ld (enemy_fast_bullet_pattern_small),a
    inc a
    ld (enemy_fast_bullet_pattern_left),a
    inc a
    ld (enemy_fast_bullet_pattern_right),a
    ld a,e
    ld (enemy_fast_bullet_page),a

    ; Reserve the final Z-band destination before emitting either one or two
    ; planes.  Preserve BC: B is the dense enemy-loop counter and C the live
    ; global plane count.
    ld a,(enemy_fast_width)
    cp 17
    ld e,1
    jr c,enemy_fast_body_reserve_count_ready
    inc e
enemy_fast_body_reserve_count_ready:
    ld a,c
    add a,e
    cp 65
    ret nc
    push bc
    ld b,e
    ld a,(ix+6)
    rrca
    rrca
    rrca
    rrca
    and 7
    ; BC is already saved immediately above, so do not save it a second time
    ; inside the generic preserving allocator.
    call _mode3_depth_reserve_clobber
    ld (enemy_fast_attribute_pointer),hl
    pop bc

    ld a,(enemy_fast_width)
    cp 17
    jr nc,enemy_fast_queue_body_wide
    ld (enemy_fast_bullet_plane_width),a
    srl a
    ld e,a
    ld hl,(enemy_fast_bullet_x)
    ld d,0
    or a
    sbc hl,de
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_bullet_pattern_small)
    ld (enemy_fast_bullet_pattern),a
    xor a
    ld (enemy_fast_bullet_shift),a
    jp enemy_fast_emit_body_plane

enemy_fast_queue_body_wide:
    ld a,c
    cp 63
    ret nc
    ld a,(enemy_fast_width)
    srl a
    ld (enemy_fast_bullet_plane_width),a
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    or a
    sbc hl,de
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_bullet_pattern_left)
    ld (enemy_fast_bullet_pattern),a
    ld a,1
    ld (enemy_fast_bullet_shift),a
    call enemy_fast_emit_body_plane

    ld a,(enemy_fast_bullet_plane_width)
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    add hl,de
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_width)
    sub e
    ld (enemy_fast_bullet_plane_width),a
    ld a,(enemy_fast_bullet_pattern_right)
    ld (enemy_fast_bullet_pattern),a
    jp enemy_fast_emit_body_second_plane

enemy_fast_emit_body_plane:
    ld a,c
    cp 64
    ret nc
    ld hl,(enemy_fast_attribute_pointer)
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_shift)
    rrca
    rrca
    and $c0
    or e
    ld (hl),a
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,(enemy_fast_bullet_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_page)
    rlca
    rlca
    rlca
    rlca
    and $70
    or e
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_plane_width)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_pattern)
    ld (hl),a
    inc hl
    ld (enemy_fast_attribute_pointer),hl
    inc c
    ret

enemy_fast_emit_body_second_plane:
    ld a,c
    cp 64
    ret nc
    push bc
    ld de,(enemy_fast_attribute_pointer)
    push de
    pop hl
    ld bc,-8
    add hl,bc
    ldi
    ldi
    ldi
    ldi
    ex de,hl
    pop bc
    ld de,(enemy_fast_bullet_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_page)
    rlca
    rlca
    rlca
    rlca
    and $70
    or e
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_plane_width)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_pattern)
    ld (hl),a
    inc hl
    ld (enemy_fast_attribute_pointer),hl
    inc c
    ret

; Append an enemy projectile directly to the mode-3 attribute buffer.  The
; generic object queue remains useful for enemies, but its decoder was a
; measurable cost when all six boss shots were active.
enemy_fast_queue_bullet:
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_asset)
    cp 31
    jr z,enemy_fast_bullet_patterns_boss
    sub 6
    ld e,a
    add a,a
    add a,e
    add a,$84
    jr enemy_fast_bullet_patterns_ready
enemy_fast_bullet_patterns_boss:
    ld a,$0c
enemy_fast_bullet_patterns_ready:
    ld (enemy_fast_bullet_pattern_small),a
    ld e,a
    ld a,(enemy_fast_bullet_flags)
    bit 4,a
    jr nz,enemy_fast_bullet_patterns_flip_x
    ld a,e
    inc a
    ld (enemy_fast_bullet_pattern_left),a
    inc a
    ld (enemy_fast_bullet_pattern_right),a
    jr enemy_fast_bullet_pattern_halves_ready
enemy_fast_bullet_patterns_flip_x:
    ; A 32-pixel source is two mode-3 planes.  Horizontal mirroring must swap
    ; the source halves as well as setting FLIP_X on each half.
    ld a,e
    add a,2
    ld (enemy_fast_bullet_pattern_left),a
    dec a
    ld (enemy_fast_bullet_pattern_right),a
enemy_fast_bullet_pattern_halves_ready:
    ld a,(enemy_fast_asset)
    cp 31
    ld a,0
    jr nz,enemy_fast_bullet_page_ready
    inc a
enemy_fast_bullet_page_ready:
    ld (enemy_fast_bullet_page),a

    ld a,(enemy_fast_width)
    cp 17
    ld b,1
    jr c,enemy_fast_bullet_reserve_count_ready
    inc b
enemy_fast_bullet_reserve_count_ready:
    ld a,(_mode3_attribute_count)
    add a,b
    cp 65
    ret nc
    ld a,(ix+3)
    rrca
    rrca
    rrca
    rrca
    and 7
    jr z,enemy_fast_bullet_reserve_bucket_ready
    dec a                          ; source projectiles draw one band nearer
enemy_fast_bullet_reserve_bucket_ready:
    call _mode3_depth_reserve
    ld (enemy_fast_attribute_pointer),hl

    ld a,(enemy_fast_width)
    cp 17
    jr nc,enemy_fast_queue_bullet_wide
    ld (enemy_fast_bullet_plane_width),a
    srl a
    ld e,a
    ld hl,(enemy_fast_bullet_x)
    ld d,0
    or a
    sbc hl,de
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_bullet_pattern_small)
    ld (enemy_fast_bullet_pattern),a
    xor a
    ld (enemy_fast_bullet_shift),a
    jp enemy_fast_emit_bullet_plane

enemy_fast_queue_bullet_wide:
    ld a,(_mode3_attribute_count)
    cp 63
    ret nc
    ld a,(enemy_fast_width)
    srl a
    ld (enemy_fast_bullet_plane_width),a
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    or a
    sbc hl,de
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_bullet_pattern_left)
    ld (enemy_fast_bullet_pattern),a
    ld a,1
    ld (enemy_fast_bullet_shift),a
    call enemy_fast_emit_bullet_plane

    ld a,(enemy_fast_bullet_plane_width)
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    add hl,de
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_width)
    sub e
    ld (enemy_fast_bullet_plane_width),a
    ld a,(enemy_fast_bullet_pattern_right)
    ld (enemy_fast_bullet_pattern),a
    jp enemy_fast_emit_bullet_second_plane

enemy_fast_emit_bullet_plane:
    ld a,(_mode3_attribute_count)
    cp 64
    ret nc
    ld hl,(enemy_fast_attribute_pointer)
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_shift)
    rrca
    rrca
    and $c0
    or e
    ld (hl),a
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_flags)
    ld (hl),a
    inc hl
    ld de,(enemy_fast_bullet_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_page)
    rlca
    rlca
    rlca
    rlca
    and $70
    or e
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_plane_width)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_pattern)
    ld (hl),a
    inc hl
    ld a,(_mode3_attribute_count)
    inc a
    ld (_mode3_attribute_count),a
    ld (enemy_fast_attribute_pointer),hl
    ret

; The right half has the same top/height/flip fields as the left half.
; Reuse those four bytes instead of rebuilding their vertical projection.
enemy_fast_emit_bullet_second_plane:
    ld a,(_mode3_attribute_count)
    cp 64
    ret nc
    ld de,(enemy_fast_attribute_pointer)
    push de
    pop hl
    ld bc,-8
    add hl,bc
    ldi
    ldi
    ldi
    ldi
    ex de,hl
    ld de,(enemy_fast_bullet_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_page)
    rlca
    rlca
    rlca
    rlca
    and $70
    or e
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_plane_width)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_pattern)
    ld (hl),a
    inc hl
    ld a,(_mode3_attribute_count)
    inc a
    ld (_mode3_attribute_count),a
    ld (enemy_fast_attribute_pointer),hl
    ret

; Normal animated projectiles have a fixed page/SZ layout.  The caller has
; already selected their four-byte pattern/flip template, so emit directly
; instead of rebuilding an asset number and passing through three generic
; helper layers for every live shot.
enemy_fast_queue_normal_bullet_direct:
    ld (enemy_fast_bullet_x),hl       ; signed screen centre
    ld a,(enemy_fast_width)
    cp 17
    jr nc,enemy_fast_normal_bullet_wide

    ld a,(_mode3_attribute_count)
    cp 64
    ret nc
    ld a,(enemy_fast_width)
    srl a
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    or a
    sbc hl,de
    ld (enemy_fast_attribute_pointer),hl ; signed left X
    ld b,1
    ld a,(ix+3)
    rrca
    rrca
    rrca
    rrca
    and 7
    jr z,enemy_fast_normal_bullet_small_bucket_ready
    dec a
enemy_fast_normal_bullet_small_bucket_ready:
    call _mode3_depth_reserve
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    ld (hl),a
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_flags)
    ld (hl),a
    inc hl
    ld de,(enemy_fast_attribute_pointer)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(enemy_fast_width)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_pattern_small)
    ld (hl),a
    ld a,(_mode3_attribute_count)
    inc a
    ld (_mode3_attribute_count),a
    ret

enemy_fast_normal_bullet_wide:
    ld a,(_mode3_attribute_count)
    cp 63
    ret nc
    ld a,(enemy_fast_width)
    srl a
    ld (enemy_fast_bullet_plane_width),a
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    or a
    sbc hl,de
    ld (enemy_fast_attribute_pointer),hl ; signed left X
    ld b,2
    ld a,(ix+3)
    rrca
    rrca
    rrca
    rrca
    and 7
    jr z,enemy_fast_normal_bullet_wide_bucket_ready
    dec a
enemy_fast_normal_bullet_wide_bucket_ready:
    call _mode3_depth_reserve

    ; Keep the shared vertical bytes in BC while both records are written.
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld c,a
    ld a,0
    sbc a,0
    and 3
    or $40
    ld b,a
    ld (hl),c
    inc hl
    ld (hl),b
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_flags)
    ld (hl),a
    inc hl
    ld de,(enemy_fast_attribute_pointer)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_plane_width)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_pattern_left)
    ld (hl),a
    inc hl

    ld (hl),c
    inc hl
    ld (hl),b
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_flags)
    ld (hl),a
    inc hl
    ld de,(enemy_fast_bullet_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(enemy_fast_width)
    ld e,a
    ld a,(enemy_fast_bullet_plane_width)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_pattern_right)
    ld (hl),a
    ld a,(_mode3_attribute_count)
    add a,2
    ld (_mode3_attribute_count),a
    ret

_monosh_enemy_fast_render:
    push ix
    ld ix,_monosh_enemies
    ld a,(_monosh_enemy_active_count_value)
    or a
    jp z,enemy_fast_enemy_done
    ld b,a
    ld a,(_mode3_attribute_count)
    ld c,a
    ; Emit slots from high to low.  The shared depth queue inserts at its
    ; head, restoring the source game's ascending slot priority per bucket.
    ld a,(_monosh_enemy_active_count_value)
    dec a
    jr z,enemy_fast_enemy_loop
    ; Dense slot index * 10 without one IX add/branch per active enemy.
    ld l,a
    ld h,0
    ld e,a
    ld d,0
    add hl,hl                      ; 2n
    add hl,hl                      ; 4n
    add hl,de                      ; 5n
    add hl,hl                      ; 10n
    ld de,_monosh_enemies
    add hl,de
    push hl
    pop ix
enemy_fast_enemy_loop:
    ; The active array is dense; see the update loop above.
    ld a,(ix+1)
    cp 2
    jp z,enemy_fast_enemy_bom
    cp 5
    jp z,enemy_fast_enemy_em0
    cp 6
    jp nz,enemy_fast_enemy_next

    ; EM1 keeps its already-projected position and state in the 8-byte slot.
    ld a,(ix+4)
    ld (enemy_fast_sx),a
    ld a,(ix+5)
    ld (enemy_fast_bottom),a
    ld a,(ix+7)
    and 7
    jr z,enemy_fast_em1_closed
    dec a
    ld e,a
    ld a,(ix+6)
    cp 80
    jr nc,enemy_fast_em1_open_index_ready
    ld a,e
    add a,5
    ld e,a
    ld a,(ix+6)
    cp 54
    jr nc,enemy_fast_em1_open_index_ready
    ld a,e
    add a,5
    ld e,a
enemy_fast_em1_open_index_ready:
    ld a,e
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_em1_open_geometry
    add hl,de
    ld a,(hl)
    ld (enemy_fast_width),a
    inc hl
    ld a,(hl)
    ld (enemy_fast_height),a
    ld a,(_monosh_em1_animation_assets_ready)
    or a
    ld a,11
    jr z,enemy_fast_em1_asset_ready
    ld a,(ix+7)
    and 7
    add a,31
    jr enemy_fast_em1_asset_ready

enemy_fast_em1_closed:
    ld a,(ix+6)
    cp 111
    jr c,enemy_fast_em1_closed_z_ready
    ld a,110
enemy_fast_em1_closed_z_ready:
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_em1_closed_geometry
    add hl,de
    ld a,(hl)
    ld (enemy_fast_width),a
    inc hl
    ld a,(hl)
    ld (enemy_fast_height),a
    ld a,11

enemy_fast_em1_asset_ready:
    ld (enemy_fast_asset),a
    ; The slot Y is the formation's centre line.  Use it directly as the
    ; sprite bottom anchor: compared with the old centre anchoring this lifts
    ; every EM1 by exactly half of its current depth-scaled picture height.
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(_monosh_ground_screen_delta)
    add a,e
    ld (enemy_fast_bottom),a
    ld a,(enemy_fast_sx)
    call enemy_fast_center_x
    ; Preserve the dense-loop counter while the EM1-specific emitter uses B
    ; for plane widths.  Avoid the generic body decoder's pattern/page/shift
    ; scratch traffic on all three members of the formation.
    ld a,b
    push af
    call enemy_fast_queue_em1
    pop af
    ld b,a
    jp enemy_fast_enemy_next

enemy_fast_enemy_bom:
    ld a,(ix+4)
    ld (enemy_fast_sx),a
    ld a,(ix+5)
    ld (enemy_fast_bottom),a
    ld a,(ix+8)
    ld (enemy_fast_width),a
    ld a,(ix+9)
    ld (enemy_fast_height),a
    ld a,5
    ld (enemy_fast_asset),a
    ld a,(enemy_fast_sx)
    call enemy_fast_center_x
    call enemy_fast_queue
    jp enemy_fast_enemy_next

enemy_fast_enemy_em0:
    ; Preserve B, which is the dense outer-loop count; the specialised
    ; emitter uses B for the interpolated plane width and updates C only.
    ld a,b
    push af
    ; Retain the projected centre for the emitter so it is formed only once.
    ; Do not CPU-clip EM0 here: V9968 clipping is exact and the extra signed
    ; interval test costs more than it saves for the formations in view.
    ld a,(ix+4)
    sub 64
    ld l,a
    ld h,0
    bit 7,l
    jr z,enemy_fast_em0_center_positive
    dec h
enemy_fast_em0_center_positive:
    add hl,hl
enemy_fast_em0_center_done:
    ; EM0 has a specialised emitter, so reserve its band destination here.
    ld a,(ix+8)
    cp 17
    ld b,1
    jr c,enemy_fast_em0_reserve_count_ready
    inc b
enemy_fast_em0_reserve_count_ready:
    ld a,c
    add a,b
    cp 65
    jr nc,enemy_fast_em0_reserve_failed
    ; HL still holds the signed centre.  Keep it on the stack across the
    ; depth allocator, then atomically exchange it with the returned output
    ; pointer.  The emitter consumes centre in HL and pops its destination;
    ; this replaces four absolute pointer stores/loads and a call/return.
    push hl
    ld a,(ix+6)
    rrca
    rrca
    rrca
    rrca
    and 7
    ; B is already saved in AF for the emitter, but C is the live global
    ; plane count and must survive allocation.  The clobbering allocator's C
    ; is the bucket-local count, which would corrupt every following offset.
    call _mode3_depth_reserve
enemy_fast_em0_reserve_done:
    ex (sp),hl
    jp enemy_fast_emit_em0
enemy_fast_em0_emit_done:
enemy_fast_em0_reserve_failed:
    pop af
    ld b,a

enemy_fast_enemy_next:
enemy_fast_enemy_not_queued:
    ; Let the VDP consume one completed perspective band while the next enemy
    ; is being prepared.  The stripe descriptor now lives in fixed RAM, so
    ; this remains valid with enemy bank 2 mapped.
    call _v9968_ground_stripes_pump_preserve_bc
    ld de,-10
    add ix,de
    dec b
    jp nz,enemy_fast_enemy_loop
enemy_fast_enemy_done:
    ld a,c
    ld (_mode3_attribute_count),a
    pop ix
    ret

; Direct EM0 attribute template.  IX points at the ten-byte enemy slot and C
; is the live plane count.  All interpolated dimensions are retained.
enemy_fast_emit_em0:
    ; The allocator returns with B=1/2, so the plane-count decision
    ; made for capacity/reservation need not reload and compare width here.
    djnz enemy_fast_emit_em0_wide
    ld a,(ix+8)
    ld b,a
    ld a,b
    srl a
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ex de,hl
    pop hl
    ld a,(ix+5)
    sub (ix+9)
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    ld (hl),a
    inc hl
    ld a,(ix+9)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld (hl),b
    inc hl
    ld a,$0b
    ld (hl),a
    inc c
    jp enemy_fast_em0_emit_done

enemy_fast_emit_em0_wide:
    ld a,(ix+8)
    srl a
    ld b,a                    ; exact interpolated left-plane width
    ld e,b
    ld d,0
    or a
    sbc hl,de
    ex de,hl                  ; DE = centre - left width
    pop hl
    ld a,(ix+5)
    sub (ix+9)
    push af                       ; reuse the common top for the right plane
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(ix+9)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld (hl),b
    inc hl
    ld a,$0c
    ld (hl),a
    inc hl

    ; DE is the left edge (centre-left width).  Recover the centre with one
    ; byte add instead of repeating the VBUF-to-screen signed conversion for
    ; the right plane.
    ld a,e
    add a,b
    ld e,a
    ld a,d
    adc a,0
    ld d,a
    pop af
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(ix+9)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(ix+8)
    sub b
    ld (hl),a
    inc hl
    ld a,$0d
    ld (hl),a
    inc c
    inc c
    jp enemy_fast_em0_emit_done

; Direct EM1 body template.  HL is the signed screen centre, IX the enemy
; slot, and C the live global plane count.  Closed EM1 uses page 1 patterns
; 0..2; open poses use page 3 in consecutive three-pattern groups.
SECTION CODE_2
enemy_fast_queue_em1:
    ld (enemy_fast_bullet_x),hl
    ld a,(enemy_fast_asset)
    cp 11
    jr nz,enemy_fast_em1_direct_open
    xor a
    ld (enemy_fast_bullet_pattern_small),a
    ld a,$10
    jr enemy_fast_em1_direct_page_ready
enemy_fast_em1_direct_open:
    sub 32
    ld e,a
    add a,a
    add a,e
    ld (enemy_fast_bullet_pattern_small),a
    ld a,$30
enemy_fast_em1_direct_page_ready:
    ld (enemy_fast_bullet_page),a       ; already shifted into X-high byte

    ld a,(enemy_fast_width)
    cp 17
    ld b,1
    jr c,enemy_fast_em1_direct_reserve_ready
    inc b
enemy_fast_em1_direct_reserve_ready:
    ld a,c
    add a,b
    cp 65
    ret nc
    ld a,(ix+6)
    rrca
    rrca
    rrca
    rrca
    and 7
    call _mode3_depth_reserve
    ld (enemy_fast_attribute_pointer),hl

    ld a,(enemy_fast_width)
    cp 17
    jr nc,enemy_fast_emit_em1_wide
    ld b,a
    srl a
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    or a
    sbc hl,de
    push hl                           ; left X
    ld hl,(enemy_fast_attribute_pointer)
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    ld (hl),a
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    pop de
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_page)
    or e
    ld (hl),a
    inc hl
    ld (hl),b
    inc hl
    ld a,(enemy_fast_bullet_pattern_small)
    ld (hl),a
    inc hl
    ld (enemy_fast_attribute_pointer),hl
    inc c
    ret

enemy_fast_emit_em1_wide:
    ; Capacity was checked with the same two-plane count before allocation.
    ld a,(enemy_fast_width)
    srl a
    ld b,a                           ; left-plane width
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    or a
    sbc hl,de
    push hl                           ; left X
    ld hl,(enemy_fast_attribute_pointer)
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    pop de
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_page)
    or e
    ld (hl),a
    inc hl
    ld (hl),b
    inc hl
    ld a,(enemy_fast_bullet_pattern_small)
    inc a
    ld (hl),a
    inc hl

    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,(enemy_fast_bullet_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(enemy_fast_bullet_page)
    or e
    ld (hl),a
    inc hl
    ld a,(enemy_fast_width)
    sub b
    ld (hl),a
    inc hl
    ld a,(enemy_fast_bullet_pattern_small)
    add a,2
    ld (hl),a
    inc hl
    ld (enemy_fast_attribute_pointer),hl
    inc c
    inc c
    ret

; Boss projectiles always use page-1 patterns $0c/$0d/$0e and no flips.
; Emit them directly instead of routing six simultaneous shots through the
; generic animated-bullet scratch template.
enemy_fast_queue_boss_bullet:
    ld (enemy_fast_bullet_x),hl       ; centre X
    ld a,(enemy_fast_width)
    cp 17
    ld b,1
    jr c,enemy_fast_boss_bullet_reserve_ready
    inc b
enemy_fast_boss_bullet_reserve_ready:
    ld a,(_mode3_attribute_count)
    add a,b
    cp 65
    ret nc
    ld a,(ix+3)
    rrca
    rrca
    rrca
    rrca
    and 7
    jr z,enemy_fast_boss_bullet_bucket_ready
    dec a
enemy_fast_boss_bullet_bucket_ready:
    call _mode3_depth_reserve
    ld (enemy_fast_attribute_pointer),hl

    ld a,(enemy_fast_width)
    cp 17
    jr nc,enemy_fast_emit_boss_bullet_wide
    ld b,a
    srl a
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    or a
    sbc hl,de
    push hl
    ld hl,(enemy_fast_attribute_pointer)
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    ld (hl),a
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    pop de
    ld (hl),e
    inc hl
    ld a,d
    and 3
    or $10
    ld (hl),a
    inc hl
    ld (hl),b
    inc hl
    ld a,$0c
    ld (hl),a
    ld a,(_mode3_attribute_count)
    inc a
    ld (_mode3_attribute_count),a
    ret

enemy_fast_emit_boss_bullet_wide:
    ; Capacity was checked with the same two-plane count before allocation.
    ld a,(enemy_fast_width)
    srl a
    ld b,a
    ld e,a
    ld d,0
    ld hl,(enemy_fast_bullet_x)
    or a
    sbc hl,de
    push hl
    ld hl,(enemy_fast_attribute_pointer)
    ld a,(enemy_fast_bottom)
    ld e,a
    ld a,(enemy_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(enemy_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    pop de
    ld (hl),e
    inc hl
    ld a,d
    and 3
    or $10
    ld (hl),a
    inc hl
    ld (hl),b
    inc hl
    ld a,$0d
    ld (hl),a
    inc hl

    push bc
    push hl
    pop de
    ld bc,-8
    add hl,bc
    ldi
    ldi
    ldi
    ldi
    ex de,hl
    pop bc
    ld de,(enemy_fast_bullet_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    or $10
    ld (hl),a
    inc hl
    ld a,(enemy_fast_width)
    sub b
    ld (hl),a
    inc hl
    ld a,$0e
    ld (hl),a
    ld a,(_mode3_attribute_count)
    add a,2
    ld (_mode3_attribute_count),a
    ret

SECTION CODE_2

; Enemy bullets: six packed 7-byte records, updated and rendered each field.
_monosh_enemy_fast_render_bullets:
    push ix
    push iy
    ld a,(_monosh_enemy_bullet_count)
    or a
    jp z,enemy_fast_bullet_done
    ld (enemy_fast_left),a
    dec a
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    or a
    sbc hl,de                       ; (count-1) * 7
    ld de,_monosh_enemy_bullets
    add hl,de
    push hl
    pop ix
enemy_fast_bullet_loop:
    ld a,(ix+1)
    ld (enemy_fast_sx),a
    ld a,(ix+2)
    ld (enemy_fast_bottom),a
    ld a,(ix+6)
    bit 7,a
    jr nz,enemy_fast_bullet_boss_animation
    srl a
    srl a
    and 15
    add a,a
    add a,a
    ld e,a
    ld d,0
    ld hl,enemy_fast_bullet_animation_lut
    add hl,de
    ld a,(hl)
    ld (enemy_fast_bullet_pattern_small),a
    inc hl
    ld a,(hl)
    ld (enemy_fast_bullet_pattern_left),a
    inc hl
    ld a,(hl)
    ld (enemy_fast_bullet_pattern_right),a
    inc hl
    ld a,(hl)
    ld (enemy_fast_bullet_flags),a
    ld de,_monosh_ebullet_animation_geometry
    jr enemy_fast_bullet_geometry_ready
enemy_fast_bullet_boss_animation:
    xor a
    ld (enemy_fast_bullet_flags),a
    ld de,_monosh_ebullet4_geometry
enemy_fast_bullet_geometry_ready:
    ld a,(ix+3)
    cp 111
    jr c,enemy_fast_bullet_z_ready
    ld a,110
enemy_fast_bullet_z_ready:
    add a,a
    ld l,a
    ld h,0
    add hl,de
    ld a,(hl)
    ld (enemy_fast_width),a
    inc hl
    ld a,(hl)
    ld (enemy_fast_height),a
    ld a,(ix+6)
    bit 7,a
    jr z,enemy_fast_bullet_normal_asset
    ld a,(enemy_fast_sx)
    call enemy_fast_center_x
    call enemy_fast_queue_boss_bullet
    jp enemy_fast_bullet_next
enemy_fast_bullet_normal_asset:
    ld a,(enemy_fast_sx)
    call enemy_fast_center_x
    call enemy_fast_queue_normal_bullet_direct
enemy_fast_bullet_next:
    call _v9968_ground_stripes_pump_clobber
    ld de,-7
    add ix,de
    ld a,(enemy_fast_left)
    dec a
    ld (enemy_fast_left),a
    jp nz,enemy_fast_bullet_loop
enemy_fast_bullet_done:
    pop iy
    pop ix
    ret

; The enemy renderer always enters through bank 2, so keep these animation
; tables beside its C/data bank rather than consuming the fixed ROM window.
SECTION RODATA_2

; 0 1 2 3, Y-flipped 3 2 1 0, XY-flipped 0 1 2 3,
; X-flipped 3 2 1 0.  Each entry lasts four 60 Hz fields.  Records contain
; small/left/right pattern and flags, eliminating per-bullet pattern maths.
enemy_fast_bullet_animation_lut:
    defb $84,$85,$86,$00, $87,$88,$89,$00
    defb $8a,$8b,$8c,$00, $8d,$8e,$8f,$00
    defb $8d,$8e,$8f,$20, $8a,$8b,$8c,$20
    defb $87,$88,$89,$20, $84,$85,$86,$20
    defb $84,$86,$85,$30, $87,$89,$88,$30
    defb $8a,$8c,$8b,$30, $8d,$8f,$8e,$30
    defb $8d,$8f,$8e,$10, $8a,$8c,$8b,$10
    defb $87,$89,$88,$10, $84,$86,$85,$10

; Index is Enemy.timer (0..48).  The values are the BOM0 master frames for
; the 0,1,2,3,2,1 loop, with eight 60 Hz fields per frame.
enemy_fast_bom_frame_by_timer:
    defb 0,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2
    defb 2,3,3,3,3,3,3,3,3,2,2,2,2,2,2,2
    defb 2,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0
    defb 0

; Enemy rendering always enters while ROM bank 2 is resident.  Keep this
; selector out of the nearly-full fixed bank.  Return A=small pattern and
; E=V9968 sprite page for the shared body emitter.
SECTION CODE_2
enemy_fast_select_bom_patterns:
    ld a,(ix+3)
    ld e,a
    ld d,0
    ld hl,enemy_fast_bom_frame_by_timer
    add hl,de
    ld a,(hl)
    or a
    jr z,enemy_fast_select_bom_frame0
    ld e,a
    add a,a
    add a,e
    add a,$3d                    ; frames 1..3 -> page-3 $40,$43,$46
    ld e,3
    ret
enemy_fast_select_bom_frame0:
    ld a,$81
    ld e,0
    ret

; The source advances its table-selected velocity once at 30 Hz.  The base
; delta is applied above every field; on the first half of each pair add the
; stored odd-velocity correction.  Thus each two 60 Hz fields sum to the
; exact signed source velocity without bringing back 30 Hz motion judder.
enemy_fast_update_bullet_dda:
    ld a,(iy+4)
    xor 1
    ld (iy+4),a
    and 1
    ret z
    ld a,(ix+1)
    add a,(iy+0)
    ld (ix+1),a
    ld a,(ix+2)
    add a,(iy+2)
    ld (ix+2),a
    ret

; EM1 uses the source state machine instead of comparing a synthetic 0..510
; 16-bit master time against every boundary.  IY+0 is the 60 Hz sub-timer and
; IY+1 is the state: split, open-far, advance-mid, open-mid, advance-near,
; open-near, gather, retreat.  Source 30 Hz deltas are split evenly between
; fields; the shrink accumulator adds 50 twice instead of source +100 once.
_monosh_enemy_fast_update_em1:
    push ix
    push iy
    xor a
    ld (enemy_fast_index),a
enemy_fast_em1_update_reseek:
    ld a,(enemy_fast_index)
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl                       ; 2 * slot
    push hl
    add hl,hl                       ; 4 * slot
    add hl,hl                       ; 8 * slot
    pop de
    add hl,de                       ; 10 * slot
    ld de,_monosh_enemies
    add hl,de
    push hl
    pop ix
    ld a,(enemy_fast_index)
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_enemy_em1_phase
    add hl,de
    push hl
    pop iy
enemy_fast_em1_update_loop:
    ld a,(enemy_fast_index)
    ld e,a
    ld a,(_monosh_enemy_active_count_value)
    cp e
    jp z,enemy_fast_em1_update_done
    jp c,enemy_fast_em1_update_done
    ld a,(ix+1)
    cp 6
    jp nz,enemy_fast_em1_update_next

    inc (iy+0)
    ld a,(iy+1)
    or a
    jp z,enemy_fast_em1_split
    cp 1
    jp z,enemy_fast_em1_open
    cp 2
    jp z,enemy_fast_em1_advance_mid
    cp 3
    jp z,enemy_fast_em1_open
    cp 4
    jp z,enemy_fast_em1_advance_near
    cp 5
    jp z,enemy_fast_em1_open
    cp 6
    jp z,enemy_fast_em1_gather
    jp enemy_fast_em1_retreat

enemy_fast_em1_split:
    ld a,(ix+2)
    and 3
    jr z,enemy_fast_em1_split_lane0
    cp 1
    jr z,enemy_fast_em1_split_lane1
    ; Lane 2: source (+4,+8) becomes (+2,+4) per 60 Hz field.
    ld a,(ix+4)
    cp 149
    jr nc,enemy_fast_em1_split_lane2_x_done
    add a,2
    cp 150
    jr c,enemy_fast_em1_split_lane2_x_store
    ld a,149
enemy_fast_em1_split_lane2_x_store:
    ld (ix+4),a
enemy_fast_em1_split_lane2_x_done:
    jr enemy_fast_em1_split_bottom_144
enemy_fast_em1_split_lane1:
    ld a,(ix+4)
    cp 108
    jr c,enemy_fast_em1_split_lane1_x_done
    sub 2
    cp 107
    jr nc,enemy_fast_em1_split_lane1_x_store
    ld a,107
enemy_fast_em1_split_lane1_x_store:
    ld (ix+4),a
enemy_fast_em1_split_lane1_x_done:
enemy_fast_em1_split_bottom_144:
    ld a,(ix+5)
    cp 144
    jr nc,enemy_fast_em1_split_motion_done
    add a,4
    cp 145
    jr c,enemy_fast_em1_split_bottom_store
    ld a,144
enemy_fast_em1_split_bottom_store:
    ld (ix+5),a
    jr enemy_fast_em1_split_motion_done
enemy_fast_em1_split_lane0:
    ld a,(ix+5)
    cp 73
    jr c,enemy_fast_em1_split_motion_done
    sub 4
    cp 72
    jr nc,enemy_fast_em1_split_lane0_bottom_store
    ld a,72
enemy_fast_em1_split_lane0_bottom_store:
    ld (ix+5),a
enemy_fast_em1_split_motion_done:
    ; Source split also advances wz 55->48.  The old MSX timeline deferred
    ; this into a separate eight-field phase, making every formation late.
    ld a,(ix+6)
    cp 97
    jr c,enemy_fast_em1_split_depth_done
    sub 2
    cp 96
    jr nc,enemy_fast_em1_split_depth_store
    ld a,96
enemy_fast_em1_split_depth_store:
    ld (ix+6),a
enemy_fast_em1_split_depth_done:
    xor a
    ld (ix+7),a
    ld a,(iy+0)
    cp 12
    jp c,enemy_fast_em1_update_next
    xor a
    ld (iy+0),a
    inc a
    ld (iy+1),a                    ; open far
    jp enemy_fast_em1_update_next

enemy_fast_em1_advance_mid:
    ld e,66
    ld d,3                         ; next state = open mid
    ld c,2
    jr enemy_fast_em1_advance
enemy_fast_em1_advance_near:
    ld e,40
    ld d,5                         ; next state = open near
    ld c,2
    ; Restore the source formation-specific third approach.  Pattern bits
    ; 7..6 are final_group; low bits remain the triangle lane.
    ld a,(ix+2)
    and $c0
    jr z,enemy_fast_em1_advance
    ld c,4
    cp $80
    jr z,enemy_fast_em1_advance
    ld c,6
enemy_fast_em1_advance:
    xor a
    ld (ix+7),a
    ld a,(ix+6)
    cp e
    jr z,enemy_fast_em1_advance_reached
    sub c
    cp e
    jr nc,enemy_fast_em1_advance_store
    ld a,e
enemy_fast_em1_advance_store:
    ld (ix+6),a
    cp e
    jp nz,enemy_fast_em1_update_next
enemy_fast_em1_advance_reached:
    xor a
    ld (iy+0),a
    ld a,d
    ld (iy+1),a
    jp enemy_fast_em1_update_next

; Open/hold/close is the source 61-frame envelope expanded to 122 fields.
; The compact table already contains those exact inserted intermediate fields.
enemy_fast_em1_open:
    ld a,(iy+0)
    dec a                            ; local 0..121
    cp 122
    jr nc,enemy_fast_em1_open_done
    ld e,a
    ld d,0
    ld hl,enemy_fast_em1_display_by_local
    add hl,de
    ld a,(hl)
    ld (ix+7),a
    ld a,(ix+2)
    and 3
    ld d,60
    or a
    jr z,enemy_fast_em1_fire_time_ready
    ld d,72
    cp 2
    jr nz,enemy_fast_em1_fire_time_ready
    ld d,66
enemy_fast_em1_fire_time_ready:
    ld a,e
    cp d
    jp nz,enemy_fast_em1_update_next
    push ix
    push iy
    push ix
    pop hl
    call _monosh_enemy_fire_em1_fast
    pop iy
    pop ix
    jp enemy_fast_em1_update_next
enemy_fast_em1_open_done:
    xor a
    ld (iy+0),a
    ld (ix+7),a
    ld a,(iy+1)
    cp 1
    jr z,enemy_fast_em1_open_to_mid
    cp 3
    jr z,enemy_fast_em1_open_to_near
    ld (iy+1),6                    ; gather
    jp enemy_fast_em1_update_next
enemy_fast_em1_open_to_mid:
    ld (iy+1),2
    jp enemy_fast_em1_update_next
enemy_fast_em1_open_to_near:
    ld (iy+1),4
    jp enemy_fast_em1_update_next

enemy_fast_em1_gather:
    xor a
    ld (ix+7),a
    ld a,(ix+4)
    cp 128
    jr z,enemy_fast_em1_gather_bottom
    jr c,enemy_fast_em1_gather_x_inc
    dec a
    jr enemy_fast_em1_gather_x_store
enemy_fast_em1_gather_x_inc:
    inc a
enemy_fast_em1_gather_x_store:
    ld (ix+4),a
enemy_fast_em1_gather_bottom:
    ld a,(ix+5)
    cp 120
    jr z,enemy_fast_em1_gather_shrink
    jr c,enemy_fast_em1_gather_bottom_inc
    dec a
    jr enemy_fast_em1_gather_bottom_store
enemy_fast_em1_gather_bottom_inc:
    inc a
enemy_fast_em1_gather_bottom_store:
    ld (ix+5),a
enemy_fast_em1_gather_shrink:
    ; Keep the visible return compact.  The literal source accumulator takes
    ; 90 source updates (180 VBlanks) to move Z2 40->110, which made the
    ; already-closed formation linger for roughly three seconds.  Preserve
    ; the established 60 Hz return: gather for 60 fields while advancing one
    ; interpolated Z step per field, then finish the remaining ten fields in
    ; retreat.
    ld a,(ix+6)
    cp 110
    jr nc,enemy_fast_em1_gather_depth_done
    inc a
    ld (ix+6),a
enemy_fast_em1_gather_depth_done:
    ld a,(iy+0)
    cp 60
    jp c,enemy_fast_em1_update_next
    xor a
    ld (iy+0),a
    ld a,7
    ld (iy+1),a
    jp enemy_fast_em1_update_next

enemy_fast_em1_retreat:
    ld (ix+4),128
    ld (ix+5),120
    xor a
    ld (ix+7),a
    ld a,(ix+6)
    cp 110
    jr nc,enemy_fast_em1_remove
    inc a
    ld (ix+6),a
    cp 110
    jp c,enemy_fast_em1_update_next
    jp enemy_fast_em1_remove

; Source adds 100/256 to wz at 30 Hz.  Two +50 fields have the same carries;
; each carry advances one source Z unit, i.e. two interpolated Z2 units.
enemy_fast_em1_shrink_step:
    ld a,(enemy_fast_index)
    ld e,a
    ld d,0
    ld hl,_monosh_enemy_em1_shrink
    add hl,de
    ld a,(hl)
    add a,50
    ld (hl),a
    ret nc
    ld a,(ix+6)
    add a,2
    cp 111
    jr c,enemy_fast_em1_shrink_store
    ld a,110
enemy_fast_em1_shrink_store:
    ld (ix+6),a
    ret

enemy_fast_em1_remove:
    ld a,(enemy_fast_index)
    ld l,a
    ld h,0
    call _monosh_enemy_remove_em1_fast
    ; The compacted last actor now occupies this slot.  Process it without
    ; advancing, matching the original dense-array continue path.
    jp enemy_fast_em1_update_reseek

enemy_fast_em1_update_next:
    ld de,10
    add ix,de
    ld de,2
    add iy,de
    ld a,(enemy_fast_index)
    inc a
    ld (enemy_fast_index),a
    jp enemy_fast_em1_update_loop
enemy_fast_em1_update_done:
    pop iy
    pop ix
    ret

enemy_fast_em1_display_by_local:
    defs 6,1
    defs 6,2
    defs 6,3
    defs 6,4
    defs 6,5
    defs 60,$85
    defs 6,5
    defs 6,4
    defs 6,3
    defs 6,2
    defs 6,1
    defs 2,0
