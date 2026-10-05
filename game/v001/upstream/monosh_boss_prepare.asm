SECTION bss_compiler

boss_prepare_i:          defs 1
boss_prepare_history:    defs 1
boss_prepare_delay:      defs 1
boss_prepare_z:          defs 1
boss_prepare_width:      defs 1
boss_prepare_height:     defs 1
boss_prepare_small:      defs 1
boss_prepare_left_pat:   defs 1
boss_prepare_right_pat:  defs 1
boss_prepare_pattern:    defs 1
boss_prepare_page:       defs 1
boss_prepare_shift:      defs 1
boss_prepare_plane_w:    defs 1
boss_prepare_x:          defs 2
boss_prepare_top:        defs 2
boss_prepare_attribute_pointer: defs 2
boss_prepare_depth_pointer: defs 2
boss_prepare_bucket:       defs 1
boss_prepare_order_count:  defs 1
boss_prepare_order_pos:    defs 1
boss_prepare_order_pointer: defs 2
boss_prepare_bucket_head:  defs 16
boss_prepare_bucket_next:  defs 9
boss_prepare_order:        defs 9
boss_fire_source_x:      defs 1
boss_fire_source_y:      defs 1
boss_fire_source_z:      defs 1
boss_fire_player_x:      defs 1
boss_fire_negative:      defs 1
boss_fire_velocity_base: defs 2
boss_collision_bullet_index: defs 1
boss_collision_bullet_cursor: defs 1
boss_collision_part_index: defs 1
boss_collision_hit_part: defs 1
boss_collision_best_z: defs 1
boss_collision_part_z: defs 1
boss_collision_bullet_x: defs 1
boss_collision_bullet_y: defs 1
boss_collision_bullet_z: defs 1
boss_collision_half_width: defs 1
boss_collision_half_height: defs 1
boss_collision_center_y: defs 1

SECTION CODE_1

PUBLIC _monosh_boss_prepare_render
PUBLIC _monosh_boss_fast_fire_bullet
PUBLIC _monosh_boss_frame_prepare
PUBLIC _monosh_boss_fast_check_hits
PUBLIC _monosh_boss_project_lift

EXTERN _monosh_boss_state
EXTERN _monosh_ground_screen_delta
EXTERN _boss_render_camera_delta
EXTERN _boss_age
EXTERN _boss_z_phase
EXTERN _boss_path_half
EXTERN _boss_motion_steps
EXTERN _history_head
EXTERN _boss_history_x
EXTERN _boss_history_y
EXTERN _boss_history_z
EXTERN _boss_part_x
EXTERN _boss_part_bottom
EXTERN _boss_part_z
EXTERN _boss_part_active
EXTERN _boss_part_timer
EXTERN _boss_attribute_cache
EXTERN _boss_attribute_z_cache
EXTERN _boss_attribute_cache_count
EXTERN _monosh_boss_face_geometry
EXTERN _monosh_boss_body_geometry
EXTERN _monosh_boss_bom_geometry
EXTERN _monosh_boss_bullet_velocity
EXTERN _monosh_boss_explosion_scale_low
EXTERN _monosh_boss_draw_order_base
EXTERN _monosh_boss_draw_order_mid
EXTERN _monosh_boss_prepare_fire
EXTERN _boss_player_x
EXTERN _boss_player_bottom
EXTERN _monosh_enemy_bullets
EXTERN _monosh_enemy_bullet_count
EXTERN _monosh_boss_bullet_aim
EXTERN _monosh_boss_frame
EXTERN _monosh_player_bullets
EXTERN _monosh_player_bullet_count
EXTERN _monosh_combat_reflect_bullet
EXTERN _monosh_boss_hp
EXTERN _boss_death_timer
EXTERN _boss_death_parts
EXTERN _v9968_ground_stripes_pump_clobber

; H=source world Y (0..255), L=doubled generic Z (0..110).
; Return HL = the exact doubled-screen lift:
;     2 * floor(world_y * source_scale[z] / 256)
; The first thirteen interpolated scales exceed 255.  Their high byte is
; always one, so one compact low-byte table plus the original world Y avoids
; both a 16-bit table and z88dk's general multiplication helper.
_monosh_boss_project_lift:
    ld c,h                         ; retain world Y
    ld a,l
    push af                        ; retain Z for the high-scale test
    ld e,l
    ld d,0
    ld hl,_monosh_boss_explosion_scale_low
    add hl,de
    ld e,(hl)                      ; low byte of projection scale
    ld d,0
    ld a,c                         ; 8x8 -> 16-bit shift/add product
    ld hl,0
    ld b,8
boss_project_lift_multiply:
    srl a
    jr nc,boss_project_lift_no_add
    add hl,de
boss_project_lift_no_add:
    sla e
    rl d
    djnz boss_project_lift_multiply
    ld e,h                         ; floor(world_y * scale_low / 256)
    ld d,0
    pop af
    cp 13
    jr nc,boss_project_lift_scale_ready
    ld a,e                         ; add world_y * 256 contribution
    add a,c
    ld e,a
    jr nc,boss_project_lift_scale_ready
    inc d
boss_project_lift_scale_ready:
    ex de,hl
    add hl,hl                      ; source VBUF row -> SCREEN 5 pixels
    ld a,h
    or a
    ret z
    ld hl,255                      ; byte bottom coordinate saturates here
    ret

; Probe one of the three player shots per field against nine projected parts.
; This matches the amortised Stage/enemy collision paths and caps the boss
; fire spike while retaining a maximum three-field hit/reflection latency.
; The byte path rejects by Z, then X, then Y and keeps the nearest-Z match.
_monosh_boss_fast_check_hits:
    ld a,(_monosh_player_bullet_count)
    or a
    ret z
    push ix
    ld a,(boss_collision_bullet_cursor)
    ld b,3
boss_collision_select_bullet:
    cp 3
    jr c,boss_collision_select_index_ready
    xor a
boss_collision_select_index_ready:
    ld (boss_collision_bullet_index),a
    ld e,a
    inc a
    cp 3
    jr c,boss_collision_select_next_ready
    xor a
boss_collision_select_next_ready:
    ld (boss_collision_bullet_cursor),a
    ld a,e
    add a,a
    add a,a
    add a,e
    ld e,a
    ld d,0
    ld ix,_monosh_player_bullets
    add ix,de
    ld a,(ix+0)
    cp 1
    jr z,boss_collision_bullet_found
    ld a,(boss_collision_bullet_cursor)
    djnz boss_collision_select_bullet
    pop ix
    ret

boss_collision_bullet_found:
    ld a,(ix+1)
    ld (boss_collision_bullet_x),a
    ld a,(ix+2)
    ld (boss_collision_bullet_y),a
    ; Player shots retain MonoSH's original Z units while the 60 Hz boss
    ; path uses interpolated Z2 units.  Compare both in Z2; the former direct
    ; byte comparison made every boss part at Z2 >= 57 unreachable.
    ld a,(ix+3)
    add a,a
    ld (boss_collision_bullet_z),a
    ld a,$ff
    ld (boss_collision_hit_part),a
    ld (boss_collision_best_z),a
    xor a
    ld (boss_collision_part_index),a
    ld c,9

boss_collision_part_loop:
    ld a,(boss_collision_part_index)
    ld e,a
    ld d,0
    ld hl,_boss_part_active
    add hl,de
    ld a,(hl)
    cp 1
    jp nz,boss_collision_next_part

    ld hl,_boss_part_z
    add hl,de
    ld a,(hl)
    ld (boss_collision_part_z),a
    ld e,a
    ld a,(boss_collision_bullet_z)
    sub e
    jr nc,boss_collision_depth_positive
    neg
boss_collision_depth_positive:
    cp 13
    jp nc,boss_collision_next_part

    ; Geometry index uses the clamped V9968 scale table.
    ld a,(boss_collision_part_z)
    cp 111
    jr c,boss_collision_geometry_z_ready
    ld a,110
boss_collision_geometry_z_ready:
    add a,a
    ld e,a
    ld d,0
    ld a,(boss_collision_part_index)
    or a
    ld hl,_monosh_boss_face_geometry
    jr z,boss_collision_geometry_table_ready
    ld hl,_monosh_boss_body_geometry
boss_collision_geometry_table_ready:
    add hl,de
    ld a,(hl)
    srl a
    ld (boss_collision_half_width),a
    inc hl
    ld a,(hl)
    srl a
    ld (boss_collision_half_height),a

    ld a,(boss_collision_part_index)
    ld e,a
    ld d,0
    ld hl,_boss_part_x
    add hl,de
    ld e,(hl)
    ld a,(boss_collision_bullet_x)
    sub e
    jr nc,boss_collision_x_positive
    neg
boss_collision_x_positive:
    ld e,a
    ld a,(boss_collision_half_width)
    cp e
    jp c,boss_collision_next_part

    ld a,(boss_collision_part_index)
    ld e,a
    ld d,0
    ld hl,_boss_part_bottom
    add hl,de
    ld a,(boss_collision_half_height)
    ld e,a
    ld a,(hl)
    sub e
    ld (boss_collision_center_y),a
    ld e,a
    ld a,(boss_collision_bullet_y)
    sub e
    jr nc,boss_collision_y_positive
    neg
boss_collision_y_positive:
    ld e,a
    ld a,(boss_collision_half_height)
    cp e
    jr c,boss_collision_next_part

    ld a,(boss_collision_part_z)
    ld e,a
    ld a,(boss_collision_best_z)
    cp e
    jr c,boss_collision_next_part
    jr z,boss_collision_next_part
    ld a,e
    ld (boss_collision_best_z),a
    ld a,(boss_collision_part_index)
    ld (boss_collision_hit_part),a

boss_collision_next_part:
    ld a,(boss_collision_part_index)
    inc a
    ld (boss_collision_part_index),a
    dec c
    jp nz,boss_collision_part_loop

    ld a,(boss_collision_hit_part)
    cp $ff
    jr z,boss_collision_next_bullet
    or a
    jr z,boss_collision_head_hit
    ld h,a
    ld a,(boss_collision_bullet_index)
    ld l,a
    push bc
    call _monosh_combat_reflect_bullet
    pop bc
    jr boss_collision_next_bullet

boss_collision_head_hit:
    xor a
    ld (ix+0),a
    ld a,(_monosh_player_bullet_count)
    dec a
    ld (_monosh_player_bullet_count),a
    ld a,(_monosh_boss_hp)
    or a
    jr z,boss_collision_next_bullet
    dec a
    ld (_monosh_boss_hp),a
    jr nz,boss_collision_next_bullet
    ld a,2
    ld (_monosh_boss_state),a
    xor a
    ld (_boss_death_timer),a
    ld (_boss_death_parts),a
    pop ix
    ret

boss_collision_next_bullet:
    pop ix
    ret

; Keep boss update and attribute preparation inside one bank-1 residency.
; This wrapper itself has a return address at SP+0.  A nested CALL would add
; another return address and make monosh_boss_frame() read that word as
; player_bottom, shifting every argument.  Copy the original small-C argument
; record (bottom, X, stage at SP+2/+4/+6) into a fresh call frame explicitly.
_monosh_boss_frame_prepare:
    ld hl,2
    add hl,sp
    ld e,(hl)                       ; player_bottom low
    inc hl
    ld d,(hl)                       ; player_bottom high
    inc hl
    ld c,(hl)                       ; player_x low
    inc hl
    ld b,(hl)                       ; player_x high
    inc hl
    ld a,(hl)                       ; stage_ready
    ld l,a
    ld h,0
    push hl                         ; small-C: leftmost argument first
    push bc
    push de
    call _monosh_boss_frame
    pop de
    pop de
    pop de
    jp _monosh_boss_prepare_render

; Project all nine history samples and compile their final mode-3 attributes
; on every 60 Hz field.
_monosh_boss_prepare_render:
    push ix
    ld a,(_monosh_boss_state)
    cp 1
    jp z,boss_prepare_active_fast
    cp 2
    jp z,boss_prepare_cache
    xor a
    ld (_boss_attribute_cache_count),a
    jp boss_prepare_done

; The active boss follows a deterministic ROM path and already has a stable
; per-field draw order.  Project each ordered joint and emit its attributes in
; one pass.  The former path projected all nine joints to RAM and immediately
; walked the same RAM a second time, costing about 7.5 ms by itself.
boss_prepare_active_fast:
    xor a
    ld (_boss_attribute_cache_count),a
    ld (boss_prepare_order_pos),a
    ld ix,_boss_attribute_cache

    ; boss_update() has already toggled path_half.  A set half means that the
    ; base pose at z_phase was just stored; a clear half means midpoint
    ; z_phase-1 was stored.
    ld a,(_boss_path_half)
    or a
    jr nz,boss_prepare_active_base_order
    ld a,(_boss_z_phase)
    or a
    jr nz,boss_prepare_active_mid_nonzero
    ld a,240
boss_prepare_active_mid_nonzero:
    dec a
    ld bc,_monosh_boss_draw_order_mid
    jr boss_prepare_active_order_ready
boss_prepare_active_base_order:
    ld a,(_boss_z_phase)
    ld bc,_monosh_boss_draw_order_base
boss_prepare_active_order_ready:
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,de
    add hl,bc
    ld (boss_prepare_order_pointer),hl

boss_prepare_active_loop:
    ld a,(boss_prepare_order_pos)
    ld e,a
    ld d,0
    ld hl,(boss_prepare_order_pointer)
    add hl,de
    ld a,(hl)
    ld (boss_prepare_i),a

    ; A trailing joint samples ten 60 Hz fields farther back than its
    ; predecessor.  Fetch the delay from ROM instead of maintaining a second
    ; projection-loop accumulator.
    ld e,a
    ld d,0
    ld hl,boss_prepare_active_delay
    add hl,de
    ld c,(hl)
    ld a,(_boss_age)
    cp c
    jp c,boss_prepare_active_inactive
    ld a,(_history_head)
    sub c
    and 127
    ld (boss_prepare_history),a

    ; X/Y/Z history arrays are exactly $80 bytes apart.  Resolve their shared
    ; index once, instead of performing three independent 16-bit address
    ; calculations for every joint.
    ld e,a
    ld d,0
    ld hl,_boss_history_x
    add hl,de
    ld a,(hl)
    ld (boss_prepare_x),a
    ld de,$0080
    add hl,de
    ld a,(hl)
    ld (boss_prepare_page),a      ; active-only centre-Y scratch
    add hl,de
    ld a,(hl)
    ld (boss_prepare_z),a

    ; The four per-part arrays are contiguous nine-byte columns.  Preserve
    ; one pointer and fill the columns after bottom has been calculated.
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_x
    add hl,de
    ld (boss_prepare_depth_pointer),hl

    ; Geometry is already a fully expanded Z table.  Active path Z is 0..110,
    ; so no clamp or arithmetic projection is needed here.
    ld a,(boss_prepare_z)
    add a,a
    ld e,a
    ld d,0
    ld a,(boss_prepare_i)
    or a
    ld hl,_monosh_boss_face_geometry
    jr z,boss_prepare_active_geometry_ready
    ld hl,_monosh_boss_body_geometry
boss_prepare_active_geometry_ready:
    add hl,de
    ld a,(hl)
    ld (boss_prepare_width),a
    inc hl
    ld a,(hl)
    ld (boss_prepare_height),a

    ; The generated path and the camera range guarantee a 0..255 bottom.
    ; Keep top signed for the V9968's 10-bit coordinate encoding.
    ld a,(boss_prepare_page)
    ld l,a
    ld h,0
    ld a,(_monosh_ground_screen_delta)
    ld e,a
    ld d,0
    bit 7,e
    jr z,boss_prepare_active_camera_ready
    dec d
boss_prepare_active_camera_ready:
    add hl,de
    ld a,(boss_prepare_height)
    srl a
    ld e,a
    ld d,0
    push hl
    add hl,de
    ld c,l
    pop hl
    ld a,(boss_prepare_height)
    srl a
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (boss_prepare_top),hl

    ld hl,(boss_prepare_depth_pointer)
    ld a,(boss_prepare_x)
    ld (hl),a
    ld de,9
    add hl,de
    ld (hl),c
    add hl,de
    ld a,(boss_prepare_z)
    ld (hl),a
    add hl,de
    ld (hl),1

    ; left = centre_x - width/2.  Every active boss joint stays inside the
    ; unsigned horizontal range; only top needs sign extension.
    ld a,(boss_prepare_x)
    ld l,a
    ld h,0
    ld a,(boss_prepare_width)
    srl a
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (boss_prepare_x),hl

    ld a,(boss_prepare_i)
    or a
    jr z,boss_prepare_active_face_patterns
    ld a,$06
    ld (boss_prepare_pattern),a
    jr boss_prepare_active_patterns_ready
boss_prepare_active_face_patterns:
    ld a,$09
    ld (boss_prepare_pattern),a
boss_prepare_active_patterns_ready:
    ld a,(boss_prepare_width)
    cp 17
    jp nc,boss_prepare_active_wide

    ; One-plane attribute.  IX remains the output cursor across all joints.
    push ix
    pop hl
    ld bc,(boss_prepare_top)
    ld (hl),c
    inc hl
    ld a,b
    and 3
    ld (hl),a
    inc hl
    ld a,(boss_prepare_height)
    ld (hl),a
    inc hl
    ld (hl),0
    inc hl
    ld de,(boss_prepare_x)
    ld (hl),e
    inc hl
    ld (hl),$10
    inc hl
    ld a,(boss_prepare_width)
    ld (hl),a
    inc hl
    ld a,(boss_prepare_pattern)
    ld (hl),a
    inc hl
    push hl
    pop ix
    ld a,(_boss_attribute_cache_count)
    inc a
    ld (_boss_attribute_cache_count),a
    jp boss_prepare_active_next

boss_prepare_active_wide:
    ld a,(boss_prepare_width)
    srl a
    ld (boss_prepare_plane_w),a
    push ix
    pop hl
    ld bc,(boss_prepare_top)
    ld (hl),c
    inc hl
    ld a,b
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(boss_prepare_height)
    ld (hl),a
    inc hl
    ld (hl),0
    inc hl
    ld de,(boss_prepare_x)
    ld (hl),e
    inc hl
    ld (hl),$10
    inc hl
    ld a,(boss_prepare_plane_w)
    ld (hl),a
    inc hl
    ld a,(boss_prepare_pattern)
    inc a
    ld (hl),a
    inc hl

    ld a,(boss_prepare_plane_w)
    ld e,a
    ld a,(boss_prepare_x)
    add a,e
    ld (boss_prepare_x),a
    ld a,(boss_prepare_width)
    sub e
    ld (boss_prepare_plane_w),a
    ld bc,(boss_prepare_top)
    ld (hl),c
    inc hl
    ld a,b
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(boss_prepare_height)
    ld (hl),a
    inc hl
    ld (hl),0
    inc hl
    ld de,(boss_prepare_x)
    ld (hl),e
    inc hl
    ld (hl),$10
    inc hl
    ld a,(boss_prepare_plane_w)
    ld (hl),a
    inc hl
    ld a,(boss_prepare_pattern)
    add a,2
    ld (hl),a
    inc hl
    push hl
    pop ix
    ld a,(_boss_attribute_cache_count)
    add a,2
    ld (_boss_attribute_cache_count),a
    jr boss_prepare_active_next

boss_prepare_active_inactive:
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_active
    add hl,de
    ld (hl),0

boss_prepare_active_next:
    call _v9968_ground_stripes_pump_clobber
    ld a,(boss_prepare_order_pos)
    inc a
    ld (boss_prepare_order_pos),a
    cp 9
    jp c,boss_prepare_active_loop
    ld a,(_boss_age)
    cp 255
    jr z,boss_prepare_active_finish
    ld hl,_boss_motion_steps
    add a,(hl)
    jr nc,boss_prepare_active_age_ready
    ld a,255
boss_prepare_active_age_ready:
    ld (_boss_age),a
boss_prepare_active_finish:
    jp boss_prepare_done

boss_prepare_project:
    xor a
    ld (boss_prepare_i),a
    ld (boss_prepare_delay),a
    ld a,(_history_head)
    ld (boss_prepare_history),a

boss_prepare_project_loop:
    ld a,(_boss_age)
    ld hl,boss_prepare_delay
    cp (hl)
    jp c,boss_prepare_project_inactive

    ; part_x[i] = history_x[history_index]
    ld a,(boss_prepare_history)
    ld e,a
    ld d,0
    ld hl,_boss_history_x
    add hl,de
    ld a,(hl)
    ld c,a
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_x
    add hl,de
    ld (hl),c

    ; Cache and store this part's logical Z.
    ld a,(boss_prepare_history)
    ld e,a
    ld d,0
    ld hl,_boss_history_z
    add hl,de
    ld a,(hl)
    ld (boss_prepare_z),a
    ld c,a
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_z
    add hl,de
    ld (hl),c

    ; Face and body have distinct vertical aspect tables.
    ld a,(boss_prepare_z)
    add a,a
    ld e,a
    ld d,0
    ld a,(boss_prepare_i)
    or a
    ld hl,_monosh_boss_face_geometry
    jr z,boss_prepare_project_height_table
    ld hl,_monosh_boss_body_geometry
boss_prepare_project_height_table:
    add hl,de
    inc hl
    ld a,(hl)
    ld (boss_prepare_height),a

    ; bottom = history centre + camera delta + height/2, saturated to byte.
    ld a,(boss_prepare_history)
    ld e,a
    ld d,0
    ld hl,_boss_history_y
    add hl,de
    ld l,(hl)
    ld h,0
    ld a,(_monosh_ground_screen_delta)
    ld e,a
    ld d,0
    bit 7,e
    jr z,boss_prepare_camera_signed
    dec d
boss_prepare_camera_signed:
    add hl,de
    ld a,(boss_prepare_height)
    srl a
    ld e,a
    ld d,0
    add hl,de
    bit 7,h
    jr nz,boss_prepare_bottom_zero
    ld a,h
    or a
    jr nz,boss_prepare_bottom_max
    ld c,l
    jr boss_prepare_bottom_ready
boss_prepare_bottom_zero:
    ld c,0
    jr boss_prepare_bottom_ready
boss_prepare_bottom_max:
    ld c,255
boss_prepare_bottom_ready:
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_bottom
    add hl,de
    ld (hl),c
    ld hl,_boss_part_active
    add hl,de
    ld (hl),1
    jr boss_prepare_project_next

boss_prepare_project_inactive:
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_active
    add hl,de
    ld (hl),0

boss_prepare_project_next:
    call _v9968_ground_stripes_pump_clobber
    ld a,(boss_prepare_history)
    sub 10
    and 127
    ld (boss_prepare_history),a
    ld a,(boss_prepare_delay)
    add a,10
    ld (boss_prepare_delay),a
    ld a,(boss_prepare_i)
    inc a
    ld (boss_prepare_i),a
    cp 9
    jp c,boss_prepare_project_loop
    ld a,(_boss_age)
    cp 255
    jr z,boss_prepare_cache
    inc a
    ld (_boss_age),a

boss_prepare_cache:
    xor a
    ld (_boss_attribute_cache_count),a
    ld hl,_boss_attribute_cache
    ld (boss_prepare_attribute_pointer),hl
    ld a,(_monosh_boss_state)
    cp 1
    jr nz,boss_prepare_runtime_order
    ; Active motion is deterministic.  Fetch its pre-sorted nine-joint order
    ; directly from ROM instead of rebuilding 16 buckets every field.
    ld a,(_boss_path_half)
    or a
    jr nz,boss_prepare_base_order
    ld a,(_boss_z_phase)
    or a
    jr nz,boss_prepare_mid_phase_nonzero
    ld a,240
boss_prepare_mid_phase_nonzero:
    dec a
    ld bc,_monosh_boss_draw_order_mid
    jr boss_prepare_order_phase_ready
boss_prepare_base_order:
    ld a,(_boss_z_phase)
    ld bc,_monosh_boss_draw_order_base
boss_prepare_order_phase_ready:
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,de
    add hl,bc
    ld (boss_prepare_order_pointer),hl
    ld a,9
    ld (boss_prepare_order_count),a
    xor a
    ld (boss_prepare_order_pos),a
    jp boss_prepare_cache_loop

boss_prepare_runtime_order:
    ; Build the doubled 16-band draw order used by the MSX Z2 coordinate.
    ; V9968 attribute zero is frontmost, hence flatten near bucket zero first.
    ld hl,boss_prepare_bucket_head
    ld b,16
    ld a,$ff
boss_prepare_bucket_clear:
    ld (hl),a
    inc hl
    djnz boss_prepare_bucket_clear
    xor a
    ld (boss_prepare_i),a
boss_prepare_bucket_build:
    ld e,a
    ld d,0
    ld hl,_boss_part_active
    add hl,de
    ld a,(hl)
    or a
    jr z,boss_prepare_bucket_build_next
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_z
    add hl,de
    ld a,(hl)
    srl a
    srl a
    srl a
    and $0f
    ld e,a
    ld d,0
    ld hl,boss_prepare_bucket_head
    add hl,de
    ld c,(hl)
    ld a,(boss_prepare_i)
    ld (hl),a
    ld e,a
    ld d,0
    ld hl,boss_prepare_bucket_next
    add hl,de
    ld (hl),c
boss_prepare_bucket_build_next:
    ld a,(boss_prepare_i)
    inc a
    ld (boss_prepare_i),a
    cp 9
    jr c,boss_prepare_bucket_build

    xor a
    ld (boss_prepare_order_count),a
    ld (boss_prepare_bucket),a
boss_prepare_bucket_flatten:
    ld e,a
    ld d,0
    ld hl,boss_prepare_bucket_head
    add hl,de
    ld a,(hl)
boss_prepare_bucket_flatten_chain:
    cp $ff
    jr z,boss_prepare_bucket_flatten_next
    ld c,a
    ld a,(boss_prepare_order_count)
    ld e,a
    ld d,0
    ld hl,boss_prepare_order
    add hl,de
    ld (hl),c
    inc a
    ld (boss_prepare_order_count),a
    ld e,c
    ld d,0
    ld hl,boss_prepare_bucket_next
    add hl,de
    ld a,(hl)
    jr boss_prepare_bucket_flatten_chain
boss_prepare_bucket_flatten_next:
    ld a,(boss_prepare_bucket)
    inc a
    ld (boss_prepare_bucket),a
    cp 16
    jr c,boss_prepare_bucket_flatten
    ld hl,boss_prepare_order
    ld (boss_prepare_order_pointer),hl
    xor a
    ld (boss_prepare_order_pos),a

boss_prepare_cache_loop:
    ld a,(boss_prepare_order_pos)
    ld e,a
    ld a,(boss_prepare_order_count)
    cp e
    jp z,boss_prepare_done
    ld d,0
    ld hl,(boss_prepare_order_pointer)
    add hl,de
    ld a,(hl)
    ld (boss_prepare_i),a
    ld e,a
    ld d,0
    ld hl,_boss_part_active
    add hl,de
    ld a,(hl)
    or a
    jp z,boss_prepare_cache_next
    ld c,a                       ; C = active kind (1=body, 2=BOM)

    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_z
    add hl,de
    ld a,(hl)
    cp 111
    jr c,boss_prepare_z_ready
    ld a,110
boss_prepare_z_ready:
    ld (boss_prepare_z),a
    add a,a
    ld e,a
    ld d,0

    ld a,c
    cp 2
    jr z,boss_prepare_select_bom
    ld a,(boss_prepare_i)
    or a
    jr z,boss_prepare_select_face
    ld hl,_monosh_boss_body_geometry
    add hl,de
    ld a,(hl)
    ld (boss_prepare_width),a
    inc hl
    ld a,(hl)
    ld (boss_prepare_height),a
    ld a,$06
    ld (boss_prepare_small),a
    ld a,$07
    ld (boss_prepare_left_pat),a
    ld a,$08
    ld (boss_prepare_right_pat),a
    ld a,1
    ld (boss_prepare_page),a
    jr boss_prepare_dimensions_ready

boss_prepare_select_face:
    ld hl,_monosh_boss_face_geometry
    add hl,de
    ld a,(hl)
    ld (boss_prepare_width),a
    inc hl
    ld a,(hl)
    ld (boss_prepare_height),a
    ld a,$09
    ld (boss_prepare_small),a
    ld a,$0a
    ld (boss_prepare_left_pat),a
    ld a,$0b
    ld (boss_prepare_right_pat),a
    ld a,1
    ld (boss_prepare_page),a
    jr boss_prepare_dimensions_ready

boss_prepare_select_bom:
    ld hl,_monosh_boss_bom_geometry
    add hl,de
    ld a,(hl)
    ld (boss_prepare_width),a
    inc hl
    ld a,(hl)
    ld (boss_prepare_height),a
    call boss_prepare_select_bom_patterns

boss_prepare_dimensions_ready:
    ; Signed left and top coordinates.
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_x
    add hl,de
    ld l,(hl)
    ld h,0
    ld a,(boss_prepare_width)
    srl a
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (boss_prepare_x),hl

    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_bottom
    add hl,de
    ld l,(hl)
    ld h,0
    ld a,(boss_prepare_height)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (boss_prepare_top),hl

    ld a,(boss_prepare_width)
    cp 17
    jr nc,boss_prepare_emit_wide
    ld (boss_prepare_plane_w),a
    ld a,(boss_prepare_small)
    ld (boss_prepare_pattern),a
    xor a
    ld (boss_prepare_shift),a
    call boss_prepare_emit_plane
    jr boss_prepare_cache_next

boss_prepare_emit_wide:
    ld a,(boss_prepare_width)
    srl a
    ld (boss_prepare_plane_w),a
    ld a,(boss_prepare_left_pat)
    ld (boss_prepare_pattern),a
    ld a,1
    ld (boss_prepare_shift),a
    call boss_prepare_emit_plane
    ld a,(boss_prepare_plane_w)
    ld e,a
    ld d,0
    ld hl,(boss_prepare_x)
    add hl,de
    ld (boss_prepare_x),hl
    ld a,(boss_prepare_width)
    sub e
    ld (boss_prepare_plane_w),a
    ld a,(boss_prepare_right_pat)
    ld (boss_prepare_pattern),a
    call boss_prepare_emit_second_plane

boss_prepare_cache_next:
    call _v9968_ground_stripes_pump_clobber
    ld a,(boss_prepare_order_pos)
    inc a
    ld (boss_prepare_order_pos),a
    jp boss_prepare_cache_loop

boss_prepare_done:
    ; The cache now represents this exact camera position.  During player
    ; death the boss simulation and preparation stop, and render_only uses
    ; this anchor to apply camera-only movement to the frozen attributes.
    ld a,(_monosh_ground_screen_delta)
    ld (_boss_render_camera_delta),a
    ld a,(_monosh_boss_state)
    cp 1
    call z,_monosh_boss_prepare_fire
    pop ix
    ret

boss_prepare_emit_plane:
    ld bc,(boss_prepare_top)
    ld hl,(boss_prepare_attribute_pointer)
    ld (hl),c
    inc hl
    ld a,b
    and 3
    ld e,a
    ld a,(boss_prepare_shift)
    rrca
    rrca
    and $c0
    or e
    ld (hl),a
    inc hl
    ld a,(boss_prepare_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,(boss_prepare_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(boss_prepare_page)
    rlca
    rlca
    rlca
    rlca
    and $70
    or e
    ld (hl),a
    inc hl
    ld a,(boss_prepare_plane_w)
    ld (hl),a
    inc hl
    ld a,(boss_prepare_pattern)
    ld (hl),a
    inc hl
    ld (boss_prepare_attribute_pointer),hl
    ld a,(_boss_attribute_cache_count)
    inc a
    ld (_boss_attribute_cache_count),a
    ret

; The second half of a wide part shares top, height, flags and scale with the
; first.  Copy those four bytes and emit only the horizontal attributes.
boss_prepare_emit_second_plane:
    ld de,(boss_prepare_attribute_pointer)
    push de
    pop hl
    ld bc,-8
    add hl,bc
    ldi
    ldi
    ldi
    ldi
    ex de,hl
    ld de,(boss_prepare_x)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld e,a
    ld a,(boss_prepare_page)
    rlca
    rlca
    rlca
    rlca
    and $70
    or e
    ld (hl),a
    inc hl
    ld a,(boss_prepare_plane_w)
    ld (hl),a
    inc hl
    ld a,(boss_prepare_pattern)
    ld (hl),a
    inc hl
    ld (boss_prepare_attribute_pointer),hl
    ld a,(_boss_attribute_cache_count)
    inc a
    ld (_boss_attribute_cache_count),a
    ret

; Allocate and aim one boss projectile without crossing into enemy ROM bank 2.
; Integer velocity alone cannot represent the half-pixel 60 Hz steps needed
; by the original 30 Hz trajectory.  Keep quotient and remainder separately;
; the bank-2 update distributes that remainder across every movement field.
; Select BOM0 artwork from this part's independent 112-field lifetime.  The
; table avoids division/modulo inside the nine-part boss render loop.
boss_prepare_select_bom_patterns:
    ld a,(boss_prepare_i)
    ld e,a
    ld d,0
    ld hl,_boss_part_timer
    add hl,de
    ld e,(hl)
    ld d,0
    ld hl,boss_prepare_bom_frame_by_timer
    add hl,de
    ld a,(hl)
    or a
    jr z,boss_prepare_select_bom_frame0
    ld e,a
    add a,a
    add a,e
    add a,$3d                    ; frames 1..3 -> page-3 $40,$43,$46
    ld (boss_prepare_small),a
    inc a
    ld (boss_prepare_left_pat),a
    inc a
    ld (boss_prepare_right_pat),a
    ld a,3
    ld (boss_prepare_page),a
    ret
boss_prepare_select_bom_frame0:
    ld a,$81
    ld (boss_prepare_small),a
    inc a
    ld (boss_prepare_left_pat),a
    inc a
    ld (boss_prepare_right_pat),a
    xor a
    ld (boss_prepare_page),a
    ret

_monosh_boss_fast_fire_bullet:
    push ix
    push iy
    ld a,(_monosh_enemy_bullet_count)
    cp 6
    jp nc,boss_fast_fire_failed
    ld a,(_boss_part_z)
    cp 8
    jp c,boss_fast_fire_failed
    ld (boss_fire_source_z),a
    ; The source selects one of its Z=4..55 velocity rows.  MSX depth is the
    ; 60 Hz doubled coordinate, so collapse it back to the source Z here.
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
    ld de,_monosh_boss_bullet_velocity
    add hl,de
    ld (boss_fire_velocity_base),hl

    ld a,(_boss_part_x)
    srl a
    add a,64
    ld (boss_fire_source_x),a
    ld a,(_boss_part_bottom)
    ld c,a
    ld a,(boss_fire_source_z)
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_boss_face_geometry
    add hl,de
    inc hl
    ld a,(hl)
    ; Source muzzle offset is 2*floor(sourceHeight/4).  Geometry height here
    ; is already doubled for SCREEN 5, so (height>>3)<<1 preserves the exact
    ; source rounding instead of occasionally placing the muzzle one row low.
    srl a
    srl a
    srl a
    add a,a
    ld e,a
    ld a,c
    sub e
    ld (boss_fire_source_y),a
    ld a,(_boss_player_x)
    srl a
    ; Source player_vbuf_x = 124 + source playerX/2.  boss_player_x is the
    ; absolute MSX centre (source playerX+128), giving the exact bias +60.
    add a,60
    ld (boss_fire_player_x),a

    ; Enemy projectiles are dense.  Append directly at bullet_count instead
    ; of scanning six active flags, and select the parallel five-byte aim
    ; record with the same index.
    ld a,(_monosh_enemy_bullet_count)
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    or a
    sbc hl,de                       ; index * 7
    ld de,_monosh_enemy_bullets
    add hl,de
    push hl
    pop ix

    ld a,(_monosh_enemy_bullet_count)
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,de
    ld de,_monosh_boss_bullet_aim
    add hl,de
    push hl
    pop iy
    xor a
    ld (iy+1),a
    ld (iy+3),a
    ld (iy+4),a

    ld a,(boss_fire_source_x)
    ld (ix+1),a
    ld a,(boss_fire_source_y)
    ld (ix+2),a
    ld a,(boss_fire_source_z)
    ld (ix+3),a

    ld a,(boss_fire_player_x)
    ld e,a
    ld a,(boss_fire_source_x)
    cp e
    jr c,boss_fast_fire_x_positive
    sub e
    ld e,1
    jr boss_fast_fire_x_distance
boss_fast_fire_x_positive:
    ld a,e
    ld e,0
    ld hl,boss_fire_source_x
    sub (hl)
boss_fast_fire_x_distance:
    ld c,a
    ld a,e
    ld (boss_fire_negative),a
    ld a,c
    srl a
    srl a
    call boss_fast_fire_lookup
    ld e,a
    ld a,(boss_fire_negative)
    or a
    ld a,e
    jr z,boss_fast_fire_x_store
    neg
boss_fast_fire_x_store:
    ; Split one exact source 30 Hz velocity into two interpolated 60 Hz
    ; deltas.  Arithmetic floor plus a 0/1 correction preserves signed odd
    ; velocities exactly over each pair (e.g. -5 -> -2,-3).
    ld e,a
    and 1
    ld (iy+0),a
    ld a,e
    sra a
    ld (ix+4),a

    ld a,(_boss_player_bottom)
    ld e,a
    ld a,(boss_fire_source_y)
    cp e
    jr c,boss_fast_fire_y_positive
    sub e
    ld e,1
    jr boss_fast_fire_y_distance
boss_fast_fire_y_positive:
    ld a,e
    ld e,0
    ld hl,boss_fire_source_y
    sub (hl)
boss_fast_fire_y_distance:
    ld c,a
    ld a,e
    ld (boss_fire_negative),a
    ld a,c
    srl a
    srl a
    call boss_fast_fire_lookup
    ld e,a
    ld a,(boss_fire_negative)
    or a
    ld a,e
    jr z,boss_fast_fire_y_store
    neg
boss_fast_fire_y_store:
    ld e,a
    and 1
    ld (iy+2),a
    ld a,e
    sra a
    ld (ix+5),a
    ld a,$80
    ld (ix+6),a
    ld (ix+0),1
    ld a,(_monosh_enemy_bullet_count)
    inc a
    ld (_monosh_enemy_bullet_count),a
    pop iy
    pop ix
    ld hl,1
    ret

boss_fast_fire_failed:
    pop iy
    pop ix
    ld hl,0
    ret

; A = source distance >> 2.  Return the source's exact table-generated
; round(distance*4/Z) velocity magnitude.
boss_fast_fire_lookup:
    ld e,a
    ld d,0
    ld hl,(boss_fire_velocity_base)
    add hl,de
    ld a,(hl)
    ret

SECTION RODATA_1

boss_prepare_active_delay:
    defb 0,10,20,30,40,50,60,70,80

; Index is boss_part_timer (0..112).  A newly spawned part at timer 112 is
; frame 0, then 0,1,2,3,2,1 repeats in eight-field groups.
boss_prepare_bom_frame_by_timer:
    defb 2,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0
    defb 0,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2
    defb 2,3,3,3,3,3,3,3,3,2,2,2,2,2,2,2
    defb 2,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0
    defb 0,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2
    defb 2,3,3,3,3,3,3,3,3,2,2,2,2,2,2,2
    defb 2,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0
    defb 0
