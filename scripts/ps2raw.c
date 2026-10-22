#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/io.h>

static int wib(int ms){ while(ms--){ if(!(inb(0x64)&2)) return 1; usleep(1000);} return 0; }
static void fl(void){ for(int i=0;i<256 && (inb(0x64)&1);i++) inb(0x60); }
static int cmd(unsigned char c){ if(!wib(200)) return 0; outb(c,0x64); return 1; }
static int dat(unsigned char d){ if(!wib(200)) return 0; outb(d,0x60); return 1; }
static int col(unsigned char *b,int ms){ int n=0; for(int i=0;i<ms && n<32;i++){ if(inb(0x64)&1) b[n++]=inb(0x60); else usleep(1000);} return n; }
static void pr(const char *t,unsigned char *b,int n){ printf("%-30s:",t); for(int i=0;i<n;i++) printf(" %02x",b[i]); puts(n?"":" (empty)"); }
static long irq1(void) {
  FILE *f = fopen("/proc/interrupts", "r");
  char line[512];
  long total = -1;
  if (!f) return -1;

  while (fgets(line, sizeof line, f)) {
    char *p = line;
    while (*p == ' ') p++;
    if (p[0] == '1' && p[1] == ':') {
      char *save = NULL;
      char *token = strtok_r(p + 2, " \t\n", &save);
      total = 0;
      while (token) {
        char *end = NULL;
        long value = strtol(token, &end, 10);
        if (end == token || *end != '\0') break; /* stop at IRQ action label */
        total += value; /* sum counters for every CPU */
        token = strtok_r(NULL, " \t\n", &save);
      }
      break;
    }
  }
  fclose(f);
  return total;
}

int main(int argc,char **argv){
  unsigned char b[32]; int n,cb=-1;
  /* This tool writes controller/keyboard commands; it is invasive, not read-only. */
  if(iopl(3)){ perror("iopl failed (run with sudo)"); return 1; }
  if(argc>1 && !strcmp(argv[1],"listen")){
    if (argc < 3) { fprintf(stderr, "usage: %s listen SECONDS\n", argv[0]); return 2; }
    int seconds = atoi(argv[2]);
    if (seconds < 1 || seconds > 300) { fprintf(stderr, "SECONDS must be 1..300\n"); return 2; }
    int ms=seconds*1000; long got=0;
    fl(); printf("Listening for %d ms - press/release keys on the internal keyboard now...\n",ms);
    for(int i=0;i<ms;i++){ if(inb(0x64)&1){ printf(" %02x",inb(0x60)); fflush(stdout); got++; } else usleep(1000); }
    printf("\nfinished: %ld bytes from keyboard\n",got); return 0;
  }
  printf("status port 0x64 = 0x%02x\n",inb(0x64)); fl();
  if(cmd(0x20)){ n=col(b,200); pr("cmd byte (0x20)",b,n); if(n) cb=b[0]; }
  if(cmd(0xAB)){ n=col(b,400); pr("interface test (0xAB)",b,n); }
  printf("IRQ1 before = %ld\n",irq1());
  if(dat(0xFF)){ n=col(b,1000); pr("reset 0xFF",b,n); }
  cmd(0xAD); usleep(150000); cmd(0xAE); usleep(150000); fl();
  if(cmd(0x20)){ n=col(b,200); pr("command byte after AD/AE",b,n); if(n) cb=b[0]; }
  if(dat(0xF2)){ n=col(b,1000); pr("GETID 0xF2",b,n); }
  if(dat(0xFF)){ n=col(b,1200); pr("second reset 0xFF",b,n); }
  if(cb>=0){
    printf("cmd byte = 0x%02x [bit0 IRQ-kbd=%d bit4 kbd-clock-disable=%d bit6 translate=%d]\n",
           cb,cb&1,(cb>>4)&1,(cb>>6)&1);
    unsigned char nb=cb|0x01; nb&=~0x10;
    if(nb!=cb){ if(cmd(0x60)&&dat(nb)) printf("command byte rewritten 0x%02x -> 0x%02x\n",cb,nb); }
    else puts("command byte is already correct; unchanged");
  }
  printf("IRQ1 after = %ld\n",irq1());
  return 0;
}
