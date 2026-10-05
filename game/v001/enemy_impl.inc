/* 同じ翻訳単位へ追加。元の密配列とstatic関数を再利用する。 */
#include "port.h"
#include "monosh_boss_data.h"
extern const unsigned char monosh_ebullet_animation_geometry[222];
unsigned char boss_dda_phase[6];
signed char boss_dda_x[6], boss_dda_y[6];

unsigned char monosh_enemy_fire_boss_at(unsigned char x, unsigned char y, unsigned char z)
{
    unsigned char slot, velocity, distance;
    unsigned int base;
    int dx, dy, signed_velocity;
    MonoshEnemyBullet *b;
    if (monosh_enemy_bullet_count >= 6 || z < 8 || z > 111) return 0;
    slot = monosh_enemy_bullet_count++; b = &enemy_bullets[slot];
    base = (unsigned int)((z >> 1)-4) << 6;
    dx = (monosh_player_x >> 1)+60-x; dy = monosh_player_bottom-y;
    distance = (dx < 0 ? -dx : dx) >> 2;
    velocity = monosh_boss_bullet_velocity[base+distance];
    signed_velocity = dx < 0 ? -(int)velocity : velocity;
    b->vx = signed_velocity >> 1; boss_dda_x[slot] = signed_velocity & 1;
    distance = (dy < 0 ? -dy : dy) >> 2;
    velocity = monosh_boss_bullet_velocity[base+distance];
    signed_velocity = dy < 0 ? -(int)velocity : velocity;
    b->vy = signed_velocity >> 1; boss_dda_y[slot] = signed_velocity & 1;
    b->active = 1; b->variant = 0x80; b->x = x; b->y = y; b->z = z;
    boss_dda_phase[slot] = 0;
    return 1;
}

static void remove_enemy(unsigned char slot)
{
    unsigned char last = --active_count;
    if (enemies[slot].type == ENEMY_TYPE_EM1) --monosh_enemy_em1_count;
    if (slot != last) {
        enemies[slot] = enemies[last]; em1_phase[slot] = em1_phase[last];
        monosh_enemy_em1_shrink[slot] = monosh_enemy_em1_shrink[last];
    }
    enemies[last].active = 0;
}

void fx_enemy_remove(unsigned char slot) { remove_enemy(slot); }
void fx_enemy_fire_em1(void *record)
{
    MonoshEnemy *e = record;
    fire_enemy_bullet_at(e->x, em1_screen_bottom(e), e->z);
}

void fx_enemy_em1_update(void *record, unsigned char slot)
{
    MonoshEnemy *e = record;
    unsigned char state = em1_phase[slot] >> 8;
    unsigned char time = (unsigned char)em1_phase[slot] + 1;
    unsigned char lane = e->pattern & 3, local, speed, target;
    int x;
    em1_phase[slot] = ((unsigned int)state << 8) | time;
    if (state == 0) {
        if (lane == 0) { if (e->bottom > 72) e->bottom -= 4; if (e->bottom < 72) e->bottom = 72; }
        else {
            if (lane == 1 && e->x > 107) { e->x -= 2; if (e->x < 107) e->x = 107; }
            if (lane == 2 && e->x < 149) { e->x += 2; if (e->x > 149) e->x = 149; }
            if (e->bottom < 144) { e->bottom += 4; if (e->bottom > 144) e->bottom = 144; }
        }
        if (e->z > 96) { e->z -= 2; if (e->z < 96) e->z = 96; }
        e->display = 0;
        if (time >= 12) em1_phase[slot] = 0x0100;
    } else if (state == 1 || state == 3 || state == 5) {
        local = time - 1;
        if (local >= 122) { e->display = 0; em1_phase[slot] = (unsigned int)(state+1)<<8; }
        else {
            if (local < 30) e->display = local/6 + 1;
            else if (local < 90) e->display = 0x85;
            else if (local < 120) e->display = 5-(local-90)/6;
            else e->display = 0;
            target = lane == 0 ? 60 : (lane == 2 ? 66 : 72);
            if (local == target) fire_enemy_bullet_at(e->x, em1_screen_bottom(e), e->z);
        }
    } else if (state == 2 || state == 4) {
        target = state == 2 ? 66 : 40;
        speed = 2;
        if (state == 4 && (e->pattern & 0xc0)) speed = (e->pattern & 0xc0) == 0x80 ? 4 : 6;
        x = e->z-speed;
        if (x < target) x = target;
        e->z = x; e->display = 0;
        if (e->z == target) em1_phase[slot] = (unsigned int)(state+1)<<8;
    } else if (state == 6) {
        if (e->x < 128) ++e->x; else if (e->x > 128) --e->x;
        if (e->bottom < 120) ++e->bottom; else if (e->bottom > 120) --e->bottom;
        if (e->z < 110) ++e->z;
        e->display = 0;
        if (time >= 60) em1_phase[slot] = 0x0700;
    } else {
        e->x = 128; e->bottom = 120; e->display = 0;
        if (e->z < 110) ++e->z;
        if (e->z >= 110) remove_enemy(slot);
    }
}

unsigned char monosh_enemy_fast_spawn_due(void)
{
    if (!spawn_wait) return 1;
    --spawn_wait; return 0;
}

#ifdef FX_REFERENCE
void monosh_enemy_fast_advance(void)
{
    unsigned char i = 0, fire, z;
    const MonoshEnemyPath *path;
    while (i < active_count) {
        MonoshEnemy *e = &enemies[i];
        if (e->type == ENEMY_TYPE_EM0) {
            fire = e->display;
            if (fire && --fire == 0) fire_enemy_bullet(e);
            ++e->frame; path = &monosh_enemy_paths[e->pattern];
            if (e->frame >= path->frames) { remove_enemy(i); continue; }
            fx_em0_geometry(e); e->display = fire;
            if (!e->z && (unsigned char)(e->x - (monosh_player_x/2+60) + 14) < 36 &&
                (unsigned char)(e->bottom - monosh_player_bottom + 20) < 53) player_hit = 1;
        } else if (e->type == ENEMY_TYPE_BOM0) {
            unsigned char ground;
            if (!e->frame || --e->frame == 0 || e->z < 2) { remove_enemy(i); continue; }
            z = --e->z;
            ground = monosh_enemy_ground_bottom[z] + monosh_ground_screen_delta;
            if (e->display && e->bottom < ground) {
                unsigned int next = e->bottom + 13 - e->display;
                e->bottom = next > ground ? ground : next;
                --e->display;
            } else { e->bottom = ground; e->display = 0; }
            e->width = monosh_bom_geometry[(unsigned int)z*2];
            e->height = monosh_bom_geometry[(unsigned int)z*2+1];
        }
        ++i;
    }
}

#endif
static const unsigned char *em1_geometry(const MonoshEnemy *e)
{
    unsigned char pose = e->display & 7, index;
    if (!pose) return monosh_em1_closed_geometry + (unsigned int)(e->z > 110 ? 110 : e->z)*2;
    index = pose - 1 + (e->z >= 80 ? 0 : (e->z >= 54 ? 5 : 10));
    return monosh_em1_open_geometry + index*2;
}

void monosh_enemy_fast_check_player_bullets(void)
{
    unsigned char i, bi, width, height;
    for (i = 0; i < active_count; ++i) {
        MonoshEnemy *e = &enemies[i];
        int center, bottom, dz, dx;
        const unsigned char *g;
        unsigned char closed;
        if (e->type != 5 && e->type != 6) continue;
        if (e->x < 64 || e->x >= 192) continue;
        center = ((int)e->x-64)*2;
        bottom = e->bottom;
        closed = e->type == 6 && !(e->display & 0x80);
        if (e->type == 6) {
            g = em1_geometry(e); width = g[0]/2; height = g[1];
            bottom += monosh_ground_screen_delta;
        } else { width = e->width/2; height = e->height; }
        if (closed) { if (width < 20) width = 20; if (height < 24) height = 24; }
        if (bottom < height) continue;
        for (bi = 0; bi < 3; ++bi) {
            MonoshPlayerBullet *b = &monosh_player_bullets[bi];
            if (b->active != 1) continue;
            dz = (int)e->z - (unsigned int)b->wz*2;
            if (dz < (closed ? -20 : -8) || dz > (closed ? 13 : 1)) continue;
            dx = center-b->screen_x; if (dx < 0) dx = -dx;
            if (dx > width || b->screen_y > bottom || b->screen_y < bottom-height) continue;
            if (closed) monosh_combat_reflect_bullet((unsigned int)bi | ((unsigned int)i<<8));
            else {
                b->active = 0; --monosh_player_bullet_count;
                if (e->type == 6) --monosh_enemy_em1_count;
                e->bottom = bottom;
                e->type = 2; e->frame = 48; e->display = 12;
                e->width = monosh_bom_geometry[(unsigned int)e->z*2];
                e->height = monosh_bom_geometry[(unsigned int)e->z*2+1];
            }
            break;
        }
    }
}

#ifdef FX_REFERENCE
void monosh_enemy_fast_update_bullets(void)
{
    unsigned char i = 0, last;
    while (i < monosh_enemy_bullet_count) {
        MonoshEnemyBullet *b = &enemy_bullets[i];
        unsigned char remove = 0;
        if (!(b->variant & 0x80)) b->variant = (b->variant+1)&63;
        if (b->z) --b->z;
        else if (b->active == 2) remove = 1;
        else if (!(b->variant & 0x80) || (boss_dda_phase[i]&1)) b->active = 2;
        b->x += b->vx; b->y += b->vy;
        if (b->variant & 0x80) {
            boss_dda_phase[i] ^= 1;
            if (boss_dda_phase[i]&1) { b->x += boss_dda_x[i]; b->y += boss_dda_y[i]; }
        }
        if (b->y >= 224) remove = 1;
        if (!remove && b->active == 2 && !b->z &&
            (unsigned char)(b->x-(monosh_player_x/2+60)+10) < 28 &&
            (unsigned char)(b->y-monosh_player_bottom+20) < 61) player_hit = 1;
        if (remove) {
            last = --monosh_enemy_bullet_count;
            enemy_bullets[i] = enemy_bullets[last]; enemy_bullets[last].active = 0;
            boss_dda_phase[i] = boss_dda_phase[last]; boss_dda_x[i] = boss_dda_x[last]; boss_dda_y[i] = boss_dda_y[last];
        } else ++i;
    }
}

#endif
void monosh_enemy_fast_render(void)
{
    unsigned char i = active_count;
    while (i) {
        MonoshEnemy *e = &enemies[--i];
        unsigned char asset, width, height, z;
        int x = ((int)e->x-64)*2, bottom = e->bottom;
        const unsigned char *g;
        z = e->z > 110 ? 110 : e->z;
        if (e->type == 6) {
            g = em1_geometry(e); width = g[0]; height = g[1];
            asset = (e->display & 7) ? 31+(e->display&7) : MONOSH_DRAW_EM1_CLOSED;
            bottom += monosh_ground_screen_delta;
        } else {
            width = e->width; height = e->height;
            asset = e->type == 2 ? MONOSH_DRAW_BOM0 : MONOSH_DRAW_EM0;
            if (e->type == 2) {
                unsigned char frame = (48-e->frame)/8;
                if (frame > 3) frame = 6-frame;
                if (frame) asset = 38+frame;
            }
        }
        fx_submit(x, bottom, width, height, asset, 0, z, 0);
    }
}

void monosh_enemy_fast_render_bullets(void)
{
    unsigned char i = monosh_enemy_bullet_count;
    while (i) {
        MonoshEnemyBullet *b = &enemy_bullets[--i];
        unsigned char z = b->z > 110 ? 110 : b->z;
        unsigned char asset, flags = 0, frame;
        const unsigned char *g;
        if (b->variant & 0x80) { asset = MONOSH_DRAW_BOSS_BULLET; g = monosh_ebullet_geometry[4]; }
        else {
            frame = (b->variant>>2)&15;
            if (frame < 4) asset = 6+frame;
            else if (frame < 8) { asset = 13-frame; flags = MODE3_FLIP_Y; }
            else if (frame < 12) { asset = frame-2; flags = MODE3_FLIP_X|MODE3_FLIP_Y; }
            else { asset = 21-frame; flags = MODE3_FLIP_X; }
            if (asset == 9) asset = 37;
            g = monosh_ebullet_animation_geometry;
        }
        g += (unsigned int)z*2;
        fx_submit(((int)b->x-64)*2, b->y, g[0], g[1], asset, flags, z, 0);
    }
}
