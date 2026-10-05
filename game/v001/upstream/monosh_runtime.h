#ifndef MSXSH_MONOSH_RUNTIME_H
#define MSXSH_MONOSH_RUNTIME_H

extern unsigned int monosh_runtime_frame_counter;
extern unsigned char monosh_runtime_paused;

void monosh_runtime_init(void);
void monosh_runtime_frame(void);

#endif
