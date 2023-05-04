# picky-py
 Python GUI using Pickit 3 to program PIC16F15214
 This is a simple program to offer a GUI, based on PySimpleGUI, running on Linux, to premit simple programming of a Microchip PIC16F15214 on a PICKIT3 programmer.
 The program uses [pk2cmd minus](http://kair.us/projects/pickitminus/) as the command line control of the pickit 3.
 
 ## Background
 
 We use linux in production not MS Windows. The official Microchip way of programming the PIC16F15 range of microprocessors is to use a SNAP or Pickit 4 together with MPLAB IPE (note not IDE). We experimented with that, but it is just too complex for the staff we use to program - too many steps, obscure error messages etc. Thus we decided to switch to a home-grown program and use a command line utility, also provided by MPLAB driven from our program. The command line utility works, well sort-of. It is written in Java. The Linux version can only program one chip per program launch. It took 17 seconds to launch and program the chip. We were hoping for one second per chip.  The MS Windows version has a "permanently running" version - obviously someone decided that 17 seconds was unacceptable - except on Linux.

 The previous version of Pickit (version 3) had a much faster command line option, but Microchip does not support programming pic16F15 on the pickit 3. The microcode loaded into the pickit3 as provided by Microchip does not support PIC16F15 (and many other recent chips). Open source to the rescue. Various people have enhanced both the microcode and the PK2CMD program to support more recent chips. Pickit 3 programmers are available from other suppliers and the combination of Pickit 3 and pk2cmd minus is reliable and fast (around  second to load our small program).
 
## Design goals

The main design goal is to enable an operator to program chips very quickly and with a minimum of training. The program tries very hard to identify problems (such as not plugging in the programmer, or plugging in the wrong one) in order to give simple error messages. Setting up the program in the first place, on the other hand, is not automated. It is assumed that one person will be working at any one time on one linux system. Use another computer if two programmers are needed. The program is run under normal end-user privileges. It has a fixed directory structure with fixed names.

A comprehensive log is written during the chip programming. It is not rotated neither is it cleared. Some manual housekeeping will be required for intensive use of the package.
 
## Modified packages

 In addition to pk2cmd which is used unchanged from the supplied appimage, we use a much-butchered version of [lsusb](https://github.com/gregkh/usbutils/blob/master/lsusb.py.in) to detect the existance of the pickit 3 programmer. This is renamed Pickit3detect.py.
