#ifndef MSXSH_MONOSH_FAR_BACKGROUND_H
#define MSXSH_MONOSH_FAR_BACKGROUND_H

#ifdef __ROM__
#define MONOSH_FAR_BANKED __banked
#else
#define MONOSH_FAR_BANKED
#endif

extern unsigned char monosh_far_u_offset;
extern unsigned char monosh_far_d_offset;

void monosh_far_background_upload(void) MONOSH_FAR_BANKED;
void monosh_far_background_init(unsigned char ground_offset);
void monosh_far_background_frame(unsigned char world_active,
                                 signed int player_x,
                                 unsigned char ground_offset);
void monosh_far_background_reset(unsigned char ground_offset);

#endif
