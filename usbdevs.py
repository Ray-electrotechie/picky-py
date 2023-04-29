import re
import subprocess
#Compile the regular expression once.  re.I is "ignore case" in regular expression matching.
device_re = re.compile("Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
df = subprocess.check_output("lsusb", text=True) # the "text=true" means return string, it is safe.
pickit3_devices = []
for i in df.split('\n'): #I now contains something like "Bus 002 Device 004: ID 0c76:161f JMTek, LLC."
    if i:
        info = device_re.match(i)
        if info:
            dinfo = info.groupdict() # returns dict containing named subgroups- bus, device, ID, tag
            dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device')) #combine
            if 'PICkit3' in dinfo['tag']:
                pickit3_devices.append(dinfo)
pickit_count = len(pickit3_devices)

for i in pickit3_devices:
    print(i)
    print ("\n")
print("total pickits=",pickit_count,"\n")
