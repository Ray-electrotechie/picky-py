# picky-py
 Python GUI using Pickit 3 to program PIC16F15214
 This is a simple program to offer a GUI, based on PySimpleGUI, running on Linux, to premit simple programming of a Microchip PIC16F15214 on a PICKIT3 programmer.
 The program uses [pk2cmd minus](http://kair.us/projects/pickitminus/) as the command line control of the pickit 3.
 
 ## Background
 
 We use linux in production not MS Windows. The official Microchip way of programming the PIC16F15 range of microprocessors is to use a SNAP or Pickit 4 together with MPLAB IPE (note not IDE). We experimented with that, but it is just too complex for the staff we use to program - too many steps, obscure error messages etc. Thus we decided to switch to a home-grown program and use a command line utility, also provided by MPLAB driven from our program. The command line utility works, well sort-of. It is written in Java. The Linux version can only program one chip per program launch. It took 17 seconds to launch and program the chip.

 The previous version of Pickit (version 3) had a much faster command line option, but Microchip does not support programming pic16F15 on the pickit 3. The microcode loaded into the pickit3 as provided by Microchip does not support PIC16F15 (and many other recent chips). Open source to the rescue. Various people have enhanced both the microcode and the PK2CMD program to support more recent chips. Pickit 3 are available from other suppliers and the combination of Pickit 3 and pk2cmd minus is reliable and fast (around  second to load our small program).
