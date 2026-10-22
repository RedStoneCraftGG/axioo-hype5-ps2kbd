import struct, os, mmap
t=open('/sys/firmware/acpi/tables/APIC','rb').read()
off=44; ioapics=[]; isos=[]
while off+2<=len(t):
    ty=t[off]; ln=t[off+1]
    if ln<2: break
    e=t[off:off+ln]
    if ty==1 and ln>=12:
        a=struct.unpack_from('<I',e,4)[0]; g=struct.unpack_from('<I',e,8)[0]
        ioapics.append((e[2],a,g)); print('IOAPIC id=%d addr=0x%08x gsi_base=%d'%(e[2],a,g))
    elif ty==2 and ln>=10:
        s=e[3]; g=struct.unpack_from('<I',e,4)[0]; f=struct.unpack_from('<H',e,8)[0]
        isos.append((s,g,f)); print('ISO  IRQ%d -> GSI%d flags=0x%04x polarity=%d trigger=%d'%(s,g,f,f&3,(f>>2)&3))
    elif ty==0 and ln>=8:
        print('LAPIC id=%d'%e[3])
    off+=ln
if not isos: print('ISO  : NO OVERRIDE (identity IRQ->GSI mapping)')
if ioapics:
    a,b,g=ioapics[0]
    fd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC); mm=mmap.mmap(fd,0x1000,offset=b)
    def rd(r):
        mm[0:4]=struct.pack('<I',r); return struct.unpack('<I',mm[0x10:0x14])[0]
    v=rd(1); n=((v>>16)&0xff)+1
    print('IOAPIC ver=0x%08x pin_count=%d'%(v,n))
    nm={0:'fixed',1:'lowprio',2:'SMI',3:'rsvd',4:'NMI',5:'INIT',7:'ExtINT'}
    for i in range(n):
        lo=rd(0x10+2*i); hi=rd(0x11+2*i)
        if lo==0 and hi==0: continue
        print('pin%2d GSI%2d vec=%3d %-7s pol=%d trig=%d mask=%d dst=%d'%(
            i,g+i,lo&0xff,nm.get((lo>>8)&7,'?'),(lo>>13)&1,(lo>>15)&1,(lo>>16)&1,(hi>>24)&0xff))
