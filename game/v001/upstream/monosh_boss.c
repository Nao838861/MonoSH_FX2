#include "monosh_boss.h"
#include "monosh_boss_data.h"
#include "monosh_combat.h"
#include "monosh_draw.h"
#include "monosh_enemy.h"
#include "ground_irq.h"

#define BOSS_PARTS 9u
#define BOSS_GEOMETRY(table, z) ((table) + ((unsigned int)(z) << 1))
#define BOSS_HISTORY 128u
#define BOSS_HP 16u
#define BOSS_Z_PERIOD 240u
#define BOSS_EXPLOSION_STEP 8u
#define BOSS_EXPLOSION_LIFE 112u
#define BOSS_FIRE_SHOOT 0u
#define BOSS_FIRE_WAIT_CLEAR 1u
#define BOSS_FIRE_WAIT_FAR 2u
extern signed char monosh_ground_screen_delta;

#ifdef __ROM__
unsigned char monosh_boss_fast_fire_bullet(void);
void monosh_boss_fast_check_hits(void);
unsigned int monosh_boss_project_lift(unsigned int packed) __z88dk_fastcall;
#endif

unsigned char monosh_boss_state;
unsigned char monosh_boss_hp;

unsigned char boss_part_x[BOSS_PARTS];
unsigned char boss_part_bottom[BOSS_PARTS];
unsigned char boss_part_z[BOSS_PARTS];
unsigned char boss_part_active[BOSS_PARTS];
unsigned char boss_part_timer[BOSS_PARTS];
unsigned char boss_part_fall_velocity[BOSS_PARTS];
unsigned char boss_part_fall_fraction[BOSS_PARTS];
unsigned char boss_history_x[BOSS_HISTORY];
unsigned char boss_history_y[BOSS_HISTORY];
unsigned char boss_history_z[BOSS_HISTORY];
unsigned char boss_attribute_cache[BOSS_PARTS * 2u * 8u];
unsigned char boss_attribute_z_cache[BOSS_PARTS * 2u];
unsigned char boss_attribute_cache_count;
signed char boss_render_camera_delta;
unsigned char history_head;
unsigned char boss_age;
unsigned char boss_death_timer;
unsigned char boss_death_parts;
unsigned char boss_restart_timer;
unsigned char boss_z_phase;
unsigned char boss_path_half;
unsigned char boss_motion_steps;
unsigned char boss_last_vblank;
unsigned char boss_fire_state;
unsigned char boss_fire_round;
unsigned char boss_fire_volley;
unsigned char boss_fire_shots;
unsigned char boss_fire_gap;
signed int boss_player_x;
signed int boss_player_bottom;

#define history_x boss_history_x
#define history_y boss_history_y
#define history_z boss_history_z
#define death_timer boss_death_timer
#define death_parts boss_death_parts
#define restart_timer boss_restart_timer

#ifdef __ROM__
#pragma bank 1
#endif

void monosh_boss_init(void)
{
    unsigned char i;
    monosh_boss_state = MONOSH_BOSS_STAGE;
    monosh_boss_hp = BOSS_HP;
    history_head = 0u;
    boss_z_phase = 0u;
    boss_path_half = 0u;
    boss_motion_steps = 1u;
    boss_last_vblank = (unsigned char)ground_irq_vblank_count;
    boss_age = 0u;
    death_timer = 0u;
    death_parts = 0u;
    restart_timer = 0u;
    boss_fire_state = BOSS_FIRE_SHOOT;
    boss_fire_round = 0u;
    boss_fire_volley = 0u;
    boss_fire_shots = 6u;
    boss_fire_gap = 0u;
    boss_attribute_cache_count = 0u;
    boss_render_camera_delta = monosh_ground_screen_delta;
    for (i = 0u; i != BOSS_PARTS; ++i) {
        boss_part_active[i] = 0u;
        boss_part_timer[i] = 0u;
        boss_part_fall_velocity[i] = 0u;
        boss_part_fall_fraction[i] = 0u;
    }
    for (i = 0u; i != BOSS_HISTORY; ++i) {
        history_x[i] = 128u;
        history_y[i] = 108u;
        history_z[i] = 80u;
    }
}

static void start_boss(void)
{
    monosh_boss_state = MONOSH_BOSS_ACTIVE;
    monosh_boss_hp = BOSS_HP;
    boss_z_phase = 0u;
    boss_path_half = 0u;
    boss_motion_steps = 1u;
    boss_last_vblank = (unsigned char)ground_irq_vblank_count;
    boss_age = 0u;
    history_head = 0u;
    boss_fire_state = BOSS_FIRE_SHOOT;
    boss_fire_round = 0u;
    boss_fire_volley = 0u;
    boss_fire_shots = 6u;
    boss_fire_gap = 0u;
    boss_attribute_cache_count = 0u;
    boss_render_camera_delta = monosh_ground_screen_delta;
}

static void update_parts(void)
{
    const unsigned char *px = boss_path_half ? monosh_boss_path_x_mid :
                                               monosh_boss_path_x;
    const unsigned char *py = boss_path_half ? monosh_boss_path_center_y_mid :
                                               monosh_boss_path_center_y;
    const unsigned char *pz = boss_path_half ? monosh_boss_path_z_mid :
                                               monosh_boss_path_z;
    unsigned char z = pz[boss_z_phase];
    history_head = (unsigned char)((history_head + 1u) & 127u);
    history_x[history_head] = px[boss_z_phase];
    history_y[history_head] = py[boss_z_phase];
    history_z[history_head] = z;
}

#ifndef __ROM__
static void dos_cache_boss_plane(signed int x, signed int y,
                                 unsigned char width, unsigned char height,
                                 unsigned char pattern,
                                 unsigned char size_shift,
                                 unsigned char page)
{
    unsigned int encoded;
    unsigned char *dst = boss_attribute_cache +
                         ((unsigned int)boss_attribute_cache_count << 3);
    encoded = (unsigned int)y & 0x03ffu;
    dst[0] = (unsigned char)encoded;
    dst[1] = (unsigned char)((encoded >> 8) | (size_shift << 6));
    dst[2] = height;
    dst[3] = 0u;
    encoded = (unsigned int)x & 0x03ffu;
    dst[4] = (unsigned char)encoded;
    dst[5] = (unsigned char)((encoded >> 8) | (page << 4));
    dst[6] = width;
    dst[7] = pattern;
    ++boss_attribute_cache_count;
}

static void dos_project_boss_parts(void)
{
    unsigned char i;
    unsigned char history_index = history_head;
    for (i = 0u; i != BOSS_PARTS; ++i) {
        if (boss_age < (unsigned char)(i * 10u)) {
            boss_part_active[i] = 0u;
        } else {
            unsigned char z = history_z[history_index];
            const unsigned char *geometry = i == 0u ?
                BOSS_GEOMETRY(monosh_boss_face_geometry, z) :
                BOSS_GEOMETRY(monosh_boss_body_geometry, z);
            unsigned char height = geometry[1];
            signed int bottom = (signed int)history_y[history_index] +
                                monosh_ground_screen_delta +
                                (height >> 1);
            boss_part_x[i] = history_x[history_index];
            boss_part_z[i] = z;
            if (bottom < 0) bottom = 0;
            if (bottom > 255) bottom = 255;
            boss_part_bottom[i] = (unsigned char)bottom;
            boss_part_active[i] = 1u;
        }
        history_index = (unsigned char)((history_index - 10u) & 127u);
    }
    if (boss_age != 255u) ++boss_age;
}

static void dos_cache_boss_attributes(void)
{
    unsigned char i = BOSS_PARTS;
    boss_attribute_cache_count = 0u;
    while (i != 0u) {
        unsigned char z;
        unsigned char width;
        unsigned char height;
        unsigned char small;
        unsigned char left_pattern;
        unsigned char right_pattern;
        unsigned char page;
        const unsigned char *geometry;
        signed int left;
        signed int top;
        --i;
        if (boss_part_active[i] == 0u) continue;
        z = boss_part_z[i] > 110u ? 110u : boss_part_z[i];
        if (boss_part_active[i] == 2u) {
            geometry = BOSS_GEOMETRY(monosh_boss_bom_geometry, z);
            small = 0x81u; left_pattern = 0x82u; right_pattern = 0x83u;
            page = 0u;
        } else if (i == 0u) {
            geometry = BOSS_GEOMETRY(monosh_boss_face_geometry, z);
            small = 0x09u; left_pattern = 0x0au; right_pattern = 0x0bu;
            page = 1u;
        } else {
            geometry = BOSS_GEOMETRY(monosh_boss_body_geometry, z);
            small = 0x06u; left_pattern = 0x07u; right_pattern = 0x08u;
            page = 1u;
        }
        width = geometry[0];
        height = geometry[1];
        left = (signed int)boss_part_x[i] - (width >> 1);
        top = (signed int)boss_part_bottom[i] - height;
        if (width <= 16u) {
            dos_cache_boss_plane(left, top, width, height,
                                 small, 0u, page);
        } else {
            unsigned char left_width = width >> 1;
            dos_cache_boss_plane(left, top, left_width, height,
                                 left_pattern, 1u, page);
            dos_cache_boss_plane(left + left_width, top,
                                 (unsigned char)(width - left_width), height,
                                 right_pattern, 1u, page);
        }
    }
}
#endif

static unsigned char fire_boss_bullet(signed int player_x,
                                      signed int player_bottom)
{
#ifdef __ROM__
    (void)player_x;
    (void)player_bottom;
    return monosh_boss_fast_fire_bullet();
#else
    unsigned char z = boss_part_z[0] > 110u ? 110u : boss_part_z[0];
    unsigned char muzzle_y = (unsigned char)(
        boss_part_bottom[0] -
        (BOSS_GEOMETRY(monosh_boss_face_geometry, z)[1] >> 2));
    (void)player_x;
    (void)player_bottom;
    return monosh_enemy_fire_boss_at(
        (unsigned char)((boss_part_x[0] >> 1) + 64u),
        muzzle_y, boss_part_z[0]);
#endif
}

static void update_fire(signed int player_x, signed int player_bottom)
{
    unsigned char volley_count;
    /* Source boss/fire logic runs once per 30 Hz base sample.  A clear bullet
       list can occur on the inserted midpoint field; advancing the volley
       there made later salvos use a position/Z that has no source equivalent.
       Leave midpoint fields visual-only and run this state machine on base. */
    if (boss_path_half == 0u) return;
    if (boss_z_phase > 120u || !boss_part_active[0]) return;
    if (boss_fire_state == BOSS_FIRE_WAIT_FAR) {
        if (boss_z_phase != 0u) return;
        boss_fire_round = (unsigned char)((boss_fire_round + 1u) & 3u);
        boss_fire_volley = 0u;
        boss_fire_shots = 6u;
        boss_fire_gap = 0u;
        boss_fire_state = BOSS_FIRE_SHOOT;
    } else if (boss_fire_state == BOSS_FIRE_WAIT_CLEAR) {
        if (monosh_enemy_bullet_count != 0u) return;
        ++boss_fire_volley;
        volley_count = boss_fire_round == 0u ? 3u : 2u;
        if (boss_fire_volley >= volley_count) {
            boss_fire_state = BOSS_FIRE_WAIT_FAR;
            return;
        }
        boss_fire_shots = boss_fire_volley == 1u ? 5u : 4u;
        boss_fire_gap = 0u;
        boss_fire_state = BOSS_FIRE_SHOOT;
    }
    if (boss_fire_gap != 0u) {
        --boss_fire_gap;
        return;
    }
    if (fire_boss_bullet(player_x, player_bottom)) {
        --boss_fire_shots;
        if (boss_fire_shots == 0u) boss_fire_state = BOSS_FIRE_WAIT_CLEAR;
        else boss_fire_gap = 1u;
    }
}

static void check_hits(void)
{
#ifdef __ROM__
    monosh_boss_fast_check_hits();
#else
    unsigned char bullet_index;
    if (monosh_player_bullet_count == 0u) return;

    for (bullet_index = 0u;
         bullet_index != MONOSH_PLAYER_BULLET_MAX;
         ++bullet_index) {
        MonoshPlayerBullet *bullet = &monosh_player_bullets[bullet_index];
        unsigned char part;
        unsigned char hit_part = 0xffu;
        unsigned char best_z = 0xffu;
        if (bullet->active != 1u) continue;

        /* Head and all eight trailing joints share the same projected cache.
           When silhouettes overlap, the nearest Z wins; equal-depth matches
           retain the lower (head-first) part index, matching the source. */
        for (part = 0u; part != BOSS_PARTS; ++part) {
            unsigned char z;
            unsigned char half_width;
            unsigned char half_height;
            const unsigned char *geometry;
            signed int center_y;
            signed int delta;
            if (boss_part_active[part] != 1u) continue;

            /* Player bullets retain source Z while boss history is Z2. */
            delta = (signed int)((unsigned int)bullet->wz << 1) -
                    boss_part_z[part];
            if (delta < 0) delta = -delta;
            if (delta > 12) continue;

            z = boss_part_z[part] > 110u ? 110u : boss_part_z[part];
            geometry = BOSS_GEOMETRY(
                part == 0u ? monosh_boss_face_geometry :
                             monosh_boss_body_geometry, z);
            half_width = geometry[0] >> 1;
            half_height = geometry[1] >> 1;

            delta = (signed int)bullet->screen_x - boss_part_x[part];
            if (delta < 0) delta = -delta;
            if (delta > half_width) continue;
            center_y = (signed int)boss_part_bottom[part] - half_height;
            delta = (signed int)bullet->screen_y - center_y;
            if (delta < 0) delta = -delta;
            if (delta > half_height) continue;

            if (boss_part_z[part] < best_z) {
                best_z = boss_part_z[part];
                hit_part = part;
            }
        }

        if (hit_part == 0xffu) continue;
        if (hit_part != 0u) {
            monosh_combat_reflect_bullet(
                (unsigned int)bullet_index | ((unsigned int)hit_part << 8));
            continue;
        }

        bullet->active = 0u;
        --monosh_player_bullet_count;
        if (monosh_boss_hp != 0u) --monosh_boss_hp;
        if (monosh_boss_hp == 0u) {
            monosh_boss_state = MONOSH_BOSS_DYING;
            death_timer = 0u;
            death_parts = 0u;
            return;
        }
    }
#endif
}

static unsigned int boss_explosion_scale(unsigned char z)
{
    unsigned int scale = monosh_boss_explosion_scale_low[z];
    if (z < 13u) scale += 256u;
    return scale;
}

static unsigned int boss_explosion_lift(unsigned char world_y,
                                        unsigned char z)
{
#ifdef __ROM__
    return monosh_boss_project_lift(
        ((unsigned int)world_y << 8) | (unsigned int)z);
#else
    return ((unsigned int)world_y * boss_explosion_scale(z) >> 8) << 1;
#endif
}

static void start_boss_explosion(unsigned char part)
{
    unsigned char old_z = boss_part_z[part] > 110u ?
                          110u : boss_part_z[part];
    unsigned char source_z = (unsigned char)((old_z + 1u) >> 1);
    unsigned char size = source_z >> 2;
    unsigned char z;
    const unsigned char *old_geometry;
    const unsigned char *bom_geometry;
    signed int center;
    signed int target_bottom;
    signed int ground_bottom;
    unsigned int world_y = 0u;

    if (part != 0u && size > 12u) size = 12u;
    else if (size > 13u) size = 13u;
    z = monosh_boss_bom_depth_by_size[size];
    old_geometry = BOSS_GEOMETRY(
        part == 0u ? monosh_boss_face_geometry : monosh_boss_body_geometry,
        old_z);
    bom_geometry = BOSS_GEOMETRY(monosh_boss_bom_geometry, z);

    /* Preserve the frozen joint centre exactly when its art changes to BOM0,
       then invert the source generic-object Y projection.  Storing world Y
       is the important distinction from the old screen-space gravity: as Z
       approaches, both the ground projection and the falling height are
       reprojected, so the explosion visibly drops while it grows. */
    center = (signed int)boss_part_bottom[part] - (old_geometry[1] >> 1);
    target_bottom = center + (bom_geometry[1] >> 1);
    if (target_bottom < 0) target_bottom = 0;
    if (target_bottom > 207) target_bottom = 207;
    ground_bottom = (signed int)monosh_boss_explosion_ground_bottom[z] +
                    monosh_ground_screen_delta;
    if (ground_bottom > target_bottom) {
        unsigned int difference =
            (unsigned int)(ground_bottom - target_bottom + 1) >> 1;
        unsigned int scale = boss_explosion_scale(z);
        world_y = ((difference << 8) + scale - 1u) / scale;
        if (world_y > 255u) world_y = 255u;
    }

    boss_part_z[part] = z;
    boss_part_bottom[part] = (unsigned char)target_bottom;
    boss_part_active[part] = 2u;
    boss_part_timer[part] = BOSS_EXPLOSION_LIFE;
    /* Retain the public names used by diagnostics; this byte now holds the
       source BOM0 world height, while the fraction byte is reserved. */
    boss_part_fall_velocity[part] = (unsigned char)world_y;
    boss_part_fall_fraction[part] = 0u;
}

static void boss_update(signed int player_x, signed int player_bottom)
{
    unsigned char i;
    (void)player_x;
    (void)player_bottom;
    if (monosh_boss_state == MONOSH_BOSS_ACTIVE) {
        boss_player_x = player_x;
        boss_player_bottom = player_bottom;
        /* The source advances exactly once per logic update and never runs a
           missed-VBlank catch-up loop.  At 60 Hz one call is one interpolated
           sample: base[n], midpoint[n,n+1], base[n+1].  Replaying several
           samples after a late field only creates a self-reinforcing CPU
           spike and makes motion skip visibly. */
        boss_motion_steps = 1u;
        update_parts();
        boss_path_half ^= 1u;
        if (boss_path_half == 0u) {
            ++boss_z_phase;
            if (boss_z_phase >= BOSS_Z_PERIOD) boss_z_phase = 0u;
        }
        check_hits();
    } else if (monosh_boss_state == MONOSH_BOSS_DYING) {
        unsigned char any_visible = 0u;
        for (i = 0u; i != BOSS_PARTS; ++i) {
            signed int bottom;
            unsigned int lift;
            if (boss_part_active[i] != 2u) continue;
            /* Z=0 is past the camera plane.  Do not retain a maximum-size
               explosion there: remove it on the field that reaches zero. */
            if (boss_part_z[i] == 0u) {
                boss_part_active[i] = 0u;
                continue;
            }
            if (boss_part_timer[i] != 0u) --boss_part_timer[i];
            if (boss_part_timer[i] == 0u) {
                boss_part_active[i] = 0u;
                continue;
            }
            /* Source BOM0 updates once at 30 Hz: Z-- and worldY-=6.  Z2 and
               worldY-=3 are the exact smooth 60 Hz equivalent. */
            --boss_part_z[i];
            if (boss_part_z[i] == 0u) {
                boss_part_active[i] = 0u;
                continue;
            }
            if (boss_part_fall_velocity[i] > 3u) {
                boss_part_fall_velocity[i] -= 3u;
            } else {
                boss_part_fall_velocity[i] = 0u;
            }
            lift = boss_explosion_lift(boss_part_fall_velocity[i],
                                       boss_part_z[i]);
            bottom =
                (signed int)monosh_boss_explosion_ground_bottom[
                    boss_part_z[i]] +
                monosh_ground_screen_delta - (signed int)lift;
            if (bottom < 0) bottom = 0;
            if (bottom > 207) bottom = 207;
            boss_part_bottom[i] = (unsigned char)bottom;
        }
        if ((death_timer & (BOSS_EXPLOSION_STEP - 1u)) == 0u &&
            death_parts < BOSS_PARTS) {
            i = death_parts++;
            /* A joint already at Z=0 has crossed the camera and must not
               create a one-field maximum-size remnant. */
            if (boss_part_z[i] != 0u) {
                start_boss_explosion(i);
            } else {
                boss_part_active[i] = 0u;
                boss_part_timer[i] = 0u;
            }
        }
        ++death_timer;
        for (i = 0u; i != BOSS_PARTS; ++i) {
            if (boss_part_active[i] != 0u) {
                any_visible = 1u;
                break;
            }
        }
        if (death_parts == BOSS_PARTS && !any_visible) {
            monosh_boss_state = MONOSH_BOSS_DONE;
            restart_timer = 0u;
            boss_attribute_cache_count = 0u;
        }
    } else if (monosh_boss_state == MONOSH_BOSS_DONE) {
        if (restart_timer != 255u) ++restart_timer;
    }
}

void monosh_boss_prepare_fire(void)
{
    if (monosh_boss_state == MONOSH_BOSS_ACTIVE) {
        update_fire(boss_player_x, boss_player_bottom);
    }
}

#ifndef __ROM__
void monosh_boss_prepare_render(void)
{
    if (monosh_boss_state == MONOSH_BOSS_ACTIVE) {
        dos_project_boss_parts();
        dos_cache_boss_attributes();
        monosh_boss_prepare_fire();
    } else if (monosh_boss_state == MONOSH_BOSS_DYING) {
        dos_cache_boss_attributes();
    } else {
        boss_attribute_cache_count = 0u;
    }
}
#endif

void monosh_boss_frame(unsigned char stage_ready,
                       signed int player_x,
                       signed int player_bottom)
{
    if (monosh_boss_state == MONOSH_BOSS_STAGE && stage_ready) start_boss();
    boss_update(player_x, player_bottom);
}

unsigned char monosh_boss_should_restart(void)
{
    return (unsigned char)(monosh_boss_state == MONOSH_BOSS_DONE &&
                           restart_timer >= 180u);
}
