#!/usr/bin/env python
# NAME: Picky_py
# VERSION: 1.1_04
# LICENSE: SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only
# DESCRIPTION:
#   picky_py - This program has a single goal: to make repetive uploading to the
#   PIC16F15214 chip as effortless as possible in order to process large numbers
#   of chips.
#   It is intended to work automatically i.e. the user plugs in a PCB containing the chip into
#   the Pickit3 programmer. If picky_py's operation is set to "auto", as soon as
#   the program detects the chip it will program it.
#   This has only been tested on Ubuntu Linux and is unlikely to function on windows.
#   The program for the chip is contained in an Intel standard .hex file with NO spaces in the file name
# DEPENDENCIES:
#   The gui uses unchanged external product PySimpleGUI
#   It requires a piece of hardware, a Pickit-3 configured with a special microcode supplied by pickit minus.
#   The pickit 3 is driven by an external program "Pickit minus" which is invoked in a separate process.
#   Relies on local module pickit3detect to check for the existance of the pickit 3
#  AUTHORS:
#    Ray Foulkes
# DESIGN:
#  The program is based on events, either as a result of users pushing screen buttons or
#  on time ticks. The state machine ticks at roughly half second intervals.
#  The pickit hardware is driven by the command line interface of an external program named
#  "Pickit minus" which is invoked in a separate process.
# ENVIRONMENT:
#  Written in Python 3. 
#The program imports a picky_py.json file from DEF_main_directory in order to load parameters.
#Only one programmer per PC is permitted at this time.
MICROCHIP_DEVICE_ID = 30E6
DEVICE_REVISION  = 1002
DEVICE_NAME = 'PIC16F15214'
from pickit3detect import *
import importlib
import logging
#from dataclasses import dataclass
from enum import Enum
last_resort_log=logging.getLogger() #This puts out info on the console

fail_list = [] #Used to record failures of module imports only.
some_failure = False
#This encapsulates imports to avoid presenting user with exception info.
# It is equivalent to import x as y
def import_module(x): 
    try:
        moditself =  importlib.import_module(x)
        #note moditself does not exist in case of exception.
    except ImportError as error:
        fail_list.append(error.name)
        return None
    else:
        return moditself
sys= import_module('sys')
io = import_module('io')
subprocess = import_module('subprocess')
shlex = import_module('shlex')
glob= import_module('glob')
sg= import_module('PySimpleGUI')
textwrap= import_module('textwrap')
os= import_module('os')
getpass= import_module('getpass')
runningon= import_module('platform')
grp= import_module('grp')
#operator= import_module('operator')
time=import_module('time')
pathlib=import_module('pathlib')
cjson=import_module('commentjson') # commentjson permits end-of-line comments using // or hash.
re=import_module('re')

if fail_list:
# then abandon here with fatal error plus the modules which failed to load. (config error)
    last_resort_log.critical('Fatal error \nModules failed to load='+' '.join(fail_list))
    exit(1)


chosen_hex_file = None
auto_upload = False #boolean controlled by the Auto button.
window = None
#
global file_of_results, file_of_errors
global current_user
current_user = getpass.getuser()
#Directories and files
#All the info for this program is kept in the users home directory under the directory named "DEF_main_directory"
#The logfile called "DEF_short_program_name+'_logfile'" is kept in this main directory.
#
#
DEF_version = '1.1'

DEF_short_program_name = 'picky_py' #No spaces please. Used for filenames
DEF_main_directory = '/picky_py'
DEF_log_file_name = '/'+DEF_short_program_name+'_logfile'
DEF_hex_file_dir = '/uploads'
DEF_upload_ext = 'hex'
DEF_JSON_filename = '/picky_py.json'
DEF_result_file = '/oputs' #to avoid problems of lots of outputs in spawned process
DEF_error_file = '/errors' #to avoid problems of lots of outputs in spawned process
user_home_dir = os.path.expanduser('~') #keeping stuff in the users home directory.
main_directory_path = user_home_dir+DEF_main_directory
user_log_file = main_directory_path+DEF_log_file_name #log file in main directory
result_file_path = main_directory_path+DEF_result_file

error_file_path = main_directory_path+DEF_error_file
JSON_file_path = main_directory_path + DEF_JSON_filename
upload_path = main_directory_path+DEF_hex_file_dir


# Next load the parameters from the JSON file.
#with open(JSON_file_path) as f:
#  json_data = cjson.commentjson.load(f)
  
class config:
    def __init__(self, jsonfile):
        with open(jsonfile) as f:
           self.json_data = cjson.commentjson.load(f)
    def get(self,configkey):
        return self.json_data[configkey] if configkey in self.json_data else configkey + ' is missing'
con =config(JSON_file_path)
#print(con.get('right_width_in_chars'))
right_col_width_chars = con.get('right_width_in_chars')
left_col_width_chars = con.get('left_width_in_chars')
announce_prog = f'{con.get("program_announce")} {DEF_version}'
announce_file = con.get("file_announce")
announce_no_file = con.get("file_announce_no")

Python_version = f'Python: {sg.sys.version}'
System_info = f'Operating System: {runningon.platform()}'
PySimpleGui_source = f'PySimpleGui source:{sg}'
PySimpleGui_version = f'PySimpleGui version:{sg.ver}'
TCL_version =f'TCL version:{sg.tclversion_detailed}'
exit_requested = False #set to true if the user presses the exit key.
#program exit is deferred until any uploading is finished to avoid screwing a chip.

#The program uses "pk2cmd minus" as the command line control of the pickit 3.
#It calls it from an Appimage in the main directory path
#The following command is to get the details of the chip connected.
pk2cmd_what_chip = main_directory_path+'/pk2cmd-x86_64.AppImage  -P'+DEVICE_NAME+' -I'
# for pk2cmd_program_chip see closer to use - the filename varies.
try:
	picky_py_logger = open(user_log_file,'+a')
except Exception:
	last_resort_log.exception(f'Fatal error - cannot open {user_log_file}'
                           )
picky_py_logger.write(f'\n\n\n\nNew session at {time.strftime("%d/%m/%Y %H:%M")} of {announce_prog}')
picky_py_logger.write(f'\nSystem:{runningon.platform()}')
picky_py_logger.write(f'\nPython:{sg.sys.version}')
picky_py_logger.write(f'\nPySimpleGui version:{sg.ver} is used for the GUI. See ')
picky_py_logger.write(f'\nPySimpleGui source:{sg}')
picky_py_logger.write(f'\nTCL version:{sg.tclversion_detailed}')

#Class messagey deals with PySimplegui things that have a static text field announcing something.
#Each instance manages a single window containing the message.
#Messages can time out or not. Time out is not very accurate.
#To achieve timeout, the method 'check' must be called in the infinite loop of PySimpleGui from a timeout event.
#If the message times out it is replaced by the default message
#The time-out can be cancelled during 'check' and the message replaced by the default message immediately
#A message can be declared critical so it cannot bfpe cancelled but will time out as normal
# When initialising the class give the window key string, an initial message and a timeout_real_seconds count which is the number
# of seconds before the message times out and gets replaced with default message.
# instance.message(mess,timeout,important) installs the string mess in the window, boolean timeout = True means
#   that the message will remain for at least the number of seconds declared at instantiation and
#   boolean important = True means that it cannot be cancelled (it must be replaced to remove it).
#call check(cancel) Checks for timeout but if boolean cancel = True the message will be replaced by default
#  unless the message has been declared critical.


class messagey:
    def __update_window(self,msg): #local function to update the messagecontent & the window.
        self.messagecontent = msg
        window[self.key].update(msg) 
    def __init__(self, window_key, startingmessage,timeout_real_seconds):
        self.default = '' #The "empty" message
        self.key = window_key #The key of the window showing the message
        self.real_seconds = timeout_real_seconds
        self.timing = False
        self.timeout_at = 0.0
        self.critical = False
        self.__update_window(startingmessage)
    def message(self,newmessage,timeout,important):
        if newmessage != self.messagecontent: self.__update_window(newmessage)
        self.critical = important
        self.timing = timeout
        if self.timing:
            self.timeout_at = self.real_seconds+time.monotonic()
    def check(self,cancel):
        if self.timing and ((cancel and not self.critical) or time.monotonic() > self.timeout_at):
            self.timing = False
            self.__update_window(self.default) # erase message


previous_log_str = ''
skipped_log = False
skipped_count = 0
def log_event(event_string):
    from string import Template
    global skipped_log,skipped_count,previous_log_str
    if event_string != previous_log_str :
        if skipped_log :
            #addtime = Template(previous_log_str)
            newtime=Template(previous_log_str).substitute(time=time.strftime("%d/%m/%Y %H:%M"))
            picky_py_logger.write(f'\n{newtime} repeated {str(skipped_count)} times')
            skipped_log = False
            skipped_count = 0
        newtime=Template(event_string).substitute(time=time.strftime("%d/%m/%Y %H:%M"))
        window['-REPORT-'].print(newtime)
        picky_py_logger.write(f'\n{newtime}')
        previous_log_str = event_string
    else:
        skipped_log = True
        skipped_count += 1
#programmer_command must only be called either the first time through the program OR after
#  test_command_fini has reported that the command is finished.
#Should really be a class.
def programmer_command(command):
    global file_of_results,file_of_errors,process_state,statewindow
    ##spawn process.
    file_of_results = open(result_file_path, "w")
    file_of_errors  = open(error_file_path,"w")
    #command_id = 'main_directory_path+'/pk2cmd-x86_64.AppImage  -P'+DEVICE_NAME+' -I'
    # main_directory_path+'/pk2cmd-x86_64.AppImage  -PPIC16F15214 -M -F'+upload_path+'/pic16F15214_release_1_0.X.production.hex
    #command = 'nrfutil dfu usb-serial -pkg '+chosen_hex_file+' -p '+port_to_program.device+' -b 115200'
    #print('command=',command)
    try:
        process_state = subprocess.Popen(
            shlex.split(command), shell=False, stdout=file_of_results, stderr=file_of_errors)
    except:
        picky_py_logger.write("\nERROR {} while running {}".format(sys.exc_info()[1], command))
        exit('unable to spawn subprocess')


def test_command_fini(event_string):
    global file_of_results,file_of_errors,process_state
    success = True
    finished = process_state.poll() is not None
    if finished: #then the process has finished.
        file_of_results.close()
        file_of_errors.close()
        result_size = pathlib.Path(result_file_path).stat().st_size
        error_size = pathlib.Path(error_file_path).stat().st_size
        success = not(error_size != 0)
    return finished,success #first is that the process has terminated, second that it was a success (or not)

#takes a filename and a compiled regular expression
# passes each line of the given file to the regular expression.
# returns  a dictionary containing pairs of group names and matches.
#Only useful for small files (reads file into memory)
regex_version = re.compile(r'(?P<item>Executable Version|Device File Version|OS Firmware Version):\s*(?P<info>[\d.]*)')
regex = re.compile(r'(?P<item>Device ID|Revision|Device Name)[\s]*=[\s]*(?P<info>[0-9A-F]{4}|[<>0-9A-Za-z ]*)')
def parse_file_regex(filename, re):
    thisdict = {}
    with open(filename,'r') as fp:
        for line in fp.readlines():
            m = re.match(line)
            if m is not None:
                dinfo = m.groupdict()
                thisdict[dinfo["item"]] = dinfo["info"] #Look in regex for item and info.
    return thisdict

#Here do initial checking for file to upload to determine whether user has to choose.
#check installation file structure
if not os.path.exists(main_directory_path):
    some_failure = True
    picky_py_logger.write('\nMain directory missing: should be:'+main_directory_path)
if not os.path.exists(upload_path):
    some_failure = True
    picky_py_logger.write('\nUpload directory missing: should be:'+upload_path)

#files_path = [os.path.abspath(x) for x in os.listdir()]
upload_files = glob.glob(upload_path+'/*.'+DEF_upload_ext)
if not upload_files:
    some_failure = True
    picky_py_logger.write('\nNo upload (.'+DEF_upload_ext+') files present in: '+upload_path)
    
    

if some_failure:
    last_resort_log.critical('Fatal error - file problem, see '+user_log_file)
    exit(0)
#subdict={a:json_data[a] for a in ['header'] if a in json_data}
#print(subdict)

prog_announce_text = con.get('program_announce')
announce_font = tuple(con.get('announce_font'))
auto_button_height = con.get('auto_button_height')
action_font = con.get('action_button_font')
file_ready_colour = con.get('file_ready_colour')
file_none_colour  = con.get('file_none_colour')
right_column_font = con.get('right_font')
right_column_header_text = con.get('right_header_text')
if len(upload_files) == 1:
    #there is only one choice so use it.
    chosen_hex_file = upload_files[0]
    browse_button_text = announce_file.replace('***',os.path.basename(chosen_hex_file)) #replace *** with file name.
    browse_button_color = file_ready_colour
else: 
    browse_button_text = announce_no_file
    browse_button_color = file_none_colour
    chosen_hex_file = "not yet chosen"

# Column layout  size=(left_col_width_chars,auto_button_height)
layout = [sg.vtop(
         [sg.Col([
                  [sg.FileBrowse(file_types=((announce_no_file, '*.'+DEF_upload_ext),),button_text = browse_button_text,
                     initial_folder = upload_path,tooltip = 'If there is only one file, it will be shown here.\n otherwise you need to choose.\
\nFiles can only be selected when not uploading and not in Auto', enable_events = True,
                     size=(left_col_width_chars*2,con.get("file_enter_height")),font=con.get('file_font'),button_color=browse_button_color ,key = '-FILE-',disabled=False)],
                  [sg.Button(con.get("action_button_no_programmer"),button_color='black on yellow',font = action_font,size=(left_col_width_chars,con.get("action_button_height")), key = '-ACTION-',disabled=True,
                  tooltip = 'When green push to program the chip.\nDo not unplug chip until told\nDisabled shown with font faded\nno chip to program' )],
                  [sg.Button(con.get("auto_off_text"), size=(left_col_width_chars,auto_button_height)        ,font=con.get('auto_button_font'),button_color=con.get('auto_off_colour'), key = '-AUTO-',
                  tooltip = 'If AUTO is on then any chip found\n will be immediately programmed.')],
                  [sg.Text('         ',             size=(left_col_width_chars+1,3),font=announce_font,key='-STATE-')],
                  [sg.Button('Exit', key='-E-',tooltip = 'Exit the program, ALWAYS exit this way', font = announce_font,  size=(left_col_width_chars,2))]
                 ]
                ) #from layout helper funcs. Vtop align tops of [elements]
         ,sg.Col([
                  [sg.Multiline(right_column_header_text,justification='center', size =(right_col_width_chars,2),disabled = True, expand_x = True, write_only = True, background_color = 'light blue', font = right_column_font)],
                  [sg.Multiline(prog_announce_text+DEF_version+'\n',autoscroll = True,disabled = True, expand_x = True,size = (right_col_width_chars, 
                     con.get('right_number_of_lines')),font = right_column_font,
                  key='-REPORT-',auto_refresh = True,write_only = True,tooltip = 'Report on activity. No user input here.')],
                  ],expand_x = True)]
         )
         ]

# Display the window and get values
window = sg.Window(announce_prog, layout = layout, resizable = True, margins=(0,0), element_padding=(0,0),finalize=True)

for key in ('-FILE-', '-ACTION-', '-AUTO-', '-STATE-','-E-'):
    window[key].expand(expand_x=True)

(old_width,old_height) = window.size
awaiting_chip_plugin = True
statewindow = messagey('-STATE-','',5.5) #set up the message window with blank entry and 5.5 seconds timeout.

log_event(f'  Thanks to https://www.pysimplegui.org for the simple GUI framework. Version: {PySimpleGui_version}')
log_event(f'  Thanks to https://github.com/gregkh/usbutils/blob/master/lsusb.py.in\n  Used to identify Pickit plugged into USB.')
log_event(f'  Python version = {Python_version}')
log_event(System_info)
log_event(f'{TCL_version}')
log_event(f'$time User {current_user} is logged on\n')



#The following class defines an ennumerated type, not available directly in the
#version of Python used during development. The use of strings to represent states
#was dropped in favour of the Enum class.
#The class represents all the valid states of the state machine driving this program.
class pro_st8(Enum):
    pickit_missing = 1     #the Pickit programmer has not yet been found
    pickit_inuse = 2       #A chip is in the process of being programmed
    awaiting_no_chip = 3   #The programming has finished, next must see no chip to prove removal.
    pickit_available = 4   #The pickit has been detected but is not in use.
    pic16_available = 5    #The chip has been detected in the pickit.
    awaiting_good_chip = 6 #A test is underway to see if there is a chip present
    pickit_awaiting_off =7 #A test is underway to see if there is NO chip present.
    

class prog_state:
    def __init__(self,atthemoment,before):
        self.now = atthemoment
        self.prev = before
    def change_to(self, new_state):
        #print('changing state from',self.now,' to ',new_state)
        self.now = new_state
    def current_state():
        return now
    def state_now_is(self,test):
        return self.now == test
    def state_now_is_not(self,test):
        return self.now != test
st8_of_prog = prog_state(pro_st8.pickit_missing,pro_st8.pickit_missing) #st8 == 'state'


#st8_of_prog.change_to(pro_st8.pickit_missing)
#
#Define the command outside of the main loop, just to avoid constantly re-creating it.
# Should the user change the file name, it will be re-generated correctly in that event handler.
pk2cmd_program_chip = main_directory_path+'/pk2cmd-x86_64.AppImage  -P'+DEVICE_NAME+' -M -F'+chosen_hex_file

#This is the infinite loop where all the work is done.
while True:
    if exit_requested and st8_of_prog.state_now_is_not(pro_st8.pickit_inuse): #then tidy up and leave
        break
    else:
        if exit_requested:     window['-E-'].update(text='Still uploading, please wait')
    missed_event = True
    #The following line provides the half second tick OR instant action if the user presses an enabled button.
    event, values = window.read(timeout = 500,timeout_key = "-TIMEOUT-",close = False)
    if event == '-ACTION-' and st8_of_prog.state_now_is(pro_st8.pic16_available) :
        if not auto_upload : ##should not be an action event anyway if auto is set.
            window['-ACTION-'].update('uploading to chip',disabled=True,button_color='white on black')
            programmer_command(pk2cmd_program_chip) #start uploading process here.
            log_event(' Started manual upload')
            window['-FILE-'].update(disabled = True)
            statewindow.message('Uploading,\ndo not unplug chip',False,True)
            st8_of_prog.change_to(pro_st8.pickit_inuse)
        missed_event = False
    if event == '-AUTO-':
        #do not permit auto to be turned on if there is no file chosen.
        if chosen_hex_file == None and not auto_upload :
            statewindow.message('auto is disabled\nfile must be chosen\nfirst',True,False)
            log_event(' Auto upload refused - no file yet chosen')
        else:
            auto_upload = not auto_upload
            if auto_upload :
                log_event(' Auto upload turned on')
                window['-ACTION-'].update(disabled=True)
                window['-FILE-'].update(disabled = True)
            else:
                log_event(' Auto upload turned off')
                if st8_of_prog.state_now_is_not(pro_st8.pickit_inuse):
                    window['-FILE-'].update(disabled = False,button_color = 'white on green')
                if st8_of_prog.state_now_is(pro_st8.pic16_available):
                    window['-ACTION-'].update(disabled=False)
#            window['-AUTO-'].update(text='AUTO is ON\n all inserted chips\nwill be programmed'
            window['-AUTO-'].update(text=con.get("auto_on_text")
               if auto_upload else con.get("auto_off_text"), button_color=con.get("auto_on_colour") if auto_upload else con.get("auto_off_colour"))
        missed_event = False
        
        
    if event == '-FILE-': #User has pressed the button to change the hex file to use as the program.
        temp_file = values['-FILE-']
        if temp_file: #then there is a file string returned by the user selection.
            if temp_file != chosen_hex_file: #then it is different to the current file
                log_event(f'$time Changed upload file to {temp_file}')
                chosen_hex_file = temp_file # Next reconstruct the "program the chip" command line.
                pk2cmd_program_chip = main_directory_path+'/pk2cmd-x86_64.AppImage  -P'+DEVICE_NAME+' -M -F'+chosen_hex_file # replace command
                window['-FILE-'].update(announce_file.replace('***',os.path.basename(chosen_hex_file)), button_color = 'white on green')
                if st8_of_prog.state_now_is(pro_st8.pic16_available): #The chip is available, let the user program it.
                    window['-ACTION-'].update(disabled=False)
        missed_event = False
    if event == "-TIMEOUT-":
        if st8_of_prog.state_now_is(pro_st8.pickit_awaiting_off):
            programmer_command(pk2cmd_what_chip) # Send the command to get the chip info. This time hoping for <no device>
            statewindow.message('Please remove the chip',False,True)
            st8_of_prog.change_to(pro_st8.awaiting_no_chip) #means that request made, awaiting results.
        elif st8_of_prog.state_now_is(pro_st8.awaiting_no_chip):
            proc_terminated = test_command_fini('')
            if proc_terminated[0]:  #The command has finished, whether success or not.
                if parse_file_regex(result_file_path, regex)["Device Name"] == '<no device>':
                    #then the user has removed the programmed chip.
                    st8_of_prog.change_to(pro_st8.pickit_available) # but a chip isn't
                    statewindow.message('',False,False)
                else:
                    st8_of_prog.change_to(pro_st8.pickit_awaiting_off) #if command is finished and NOT no device, go command again.
            #else if command not terminated, just await next tick with the same state.
        elif st8_of_prog.state_now_is(pro_st8.pickit_available):
            #then check for correct chip available
            programmer_command(pk2cmd_what_chip)
            log_event(f'$time Seeking {DEVICE_NAME} to programme')
            statewindow.message('Plug chip in',False,True)
            st8_of_prog.change_to(pro_st8.awaiting_good_chip) #means that request has been made, results to check
        elif st8_of_prog.state_now_is(pro_st8.awaiting_good_chip):
            proc_terminated = test_command_fini('')
            if proc_terminated[0]:
                if parse_file_regex(result_file_path, regex)["Device Name"] == DEVICE_NAME :
                    st8_of_prog.change_to(pro_st8.pic16_available)
                    window['-ACTION-'].update(text= DEVICE_NAME+'\nwill be programmed'
                       if auto_upload else "Push here to upload\n to "+DEVICE_NAME, button_color=con.get("action_disabled") if auto_upload else con.get("action_enabled"),
                       disabled=True if auto_upload or not chosen_hex_file else False)
                    statewindow.message('',False,False)
                    log_event(f'$time {DEVICE_NAME} will be programmed')
                else:
                    st8_of_prog.change_to(pro_st8.pickit_available) #Not found a device so go and test again
            #else, if not terminated, await tick but no state change.
        if st8_of_prog.state_now_is(pro_st8.pickit_missing):
            #then try to find 
            pickits = []
            get_list_pickit3(pickits)
            if len(pickits) == 1:
                #then there is a single Pickit installed. Record the info and set the state.
                current_pickit = pickits[0]
                st8_of_prog.change_to(pro_st8.pickit_available)
                window['-ACTION-'].update(text= 'Pickit 3 found,\nsearching for chip')
                statewindow.message(f' {current_pickit.product}\ndetected, serial=\n{current_pickit.serial}\n',True,False)
                log_event(f' Programmer: {current_pickit.name} {current_pickit.product} with serial= {current_pickit.serial}')
            else:
                statewindow.message('More than one\nprogrammer detected\nonly 1 permitted',True,False)
                for programmer in pickits:
                    log_event(' Programmer: '+programmer.name+programmer.product+' with serial= '+programmer.serial)
        missed_event = False
        # next line removes timed out messages.
        statewindow.check(st8_of_prog.state_now_is_not(pro_st8.pic16_available) and st8_of_prog.state_now_is_not(pro_st8.pickit_inuse)) #cancel if not awaiting chip plugin and not uploading
        if auto_upload and st8_of_prog.state_now_is(pro_st8.pic16_available):
            programmer_command(pk2cmd_program_chip) #start uploading process here.
            log_event(f'$time Started auto upload')
            window['-ACTION-'].update('uploading to chip\n',disabled=True,button_color='white on black')
            window['-FILE-'].update(disabled = True)
            statewindow.message('Uploading,\ndo not unplug chip',True,False)
            st8_of_prog.change_to(pro_st8.pickit_inuse)
        elif st8_of_prog.state_now_is(pro_st8.pickit_inuse): #Means the command to program has been sent, but perhaps not yet completed
            results = test_command_fini(' ')
            if results[0]: #The command has completed, maybe success of failed. Change state to awaiting chip change
                st8_of_prog.change_to(pro_st8.pickit_awaiting_off)
                window['-ACTION-'].update('awaiting chip\nremoval',button_color='white on orange',disabled=True)
                if results[1]: #then all is well.
                    statewindow.message('Success uploading\nunplug now',False,True)
                    msg='Successful upload'
                else:
                    #perhaps parse and report error here.
                    msg=' Failed upload'
                    statewindow.message('Failed uploading\nunplug now',False,True)
                log_event(f'$time {msg}')
                if not auto_upload:
                    window['-FILE-'].update(disabled = False)

    if event == "-E-" or event == sg.WIN_CLOSED or event == sg.WIN_CLOSED or event == 'Exit':
        exit_requested = True #only abandon if the upload is finished.
        missed_event = False
    if missed_event:
        log_event(f'\n $time Technical problem Missed event={event} values= {values}')
log_event(f'$time Exited gracefully')
picky_py_logger.close()
window.close()

#print('~\working\\'+datetime.datetime.now().time.strftime("%y%m%d_%H%M%S")+'_'+str(uuid.uuid4().hex)+'.usbres')
