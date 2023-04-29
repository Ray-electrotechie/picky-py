#!/usr/bin/env python
#
#picky_py - This program has a single goal: to make repetive uploading to the
#   PIC16F15214 chip as effortless as possible in order to do process large numbers.
#It is intended to work automatically i.e. the user plugs in a PCB containing the chip into
# the Pickit3 programmer, as soon as
#the program detects the chip it will program it.
#This has only been tested on Ubuntu Linux and is unlikely to function on windows.
#The input is a standard .hex file with NO spaces in the file name
#
#The program imports a picky_py.json file from DEF_main_directory in order to load parameters.
#Only one programmer per PC is permitted at this time.
MICROCHIP_DEVICE_ID = 30E6
DEVICE_REVISION  = 1002
DEVICE_NAME = 'PIC16F15214'
from pickit3detect import *

import importlib
import logging
from dataclasses import dataclass
from enum import Enum
last_resort_log=logging.getLogger() #This puts out info on the console

fail_list = [] #Used to record failures of module imports only.
some_failure = False
#This encapsulates imports to avoid presenting user with exception info.
# It is equivalent to import x as y
def import_module(x): 
    try:
        moditself =  importlib.import_module(x)
    except ImportError as error:
        fail_list.append(error.name)
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
operator= import_module('operator')
#serial= import_module('serial')
time=import_module('time')
pathlib=import_module('pathlib')
#seriallist_ports = import_module('serial.tools.list_ports')
json=import_module('json')
re=import_module('re')

def sprint(*args, **kwargs):
    sio = io.StringIO()
    print(*args, **kwargs, file=sio)
    return sio.getvalue()



chosen_hex_file = None
auto_upload = False #boolean controlled by the Auto button.
window = None
#
global results, errors
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
DEF_error_file = '/er  = range(1, 6)rors' #to avoid problems of lots of outputs in spawned process
user_home_dir = os.path.expanduser('~') #keeping stuff in the users home directory.
main_directory_path = user_home_dir+DEF_main_directory
user_log_file = main_directory_path+DEF_log_file_name #log file in main directory
result_file_path = main_directory_path+DEF_result_file

error_file_path = main_directory_path+DEF_error_file
JSON_file_path = main_directory_path + DEF_JSON_filename
upload_path = main_directory_path+DEF_hex_file_dir


# Next load the parameters from the JSON file.
with open(JSON_file_path) as f:
  json_data = json.load(f)
  
right_col_width_chars = json_data['picky_py_config']['right_column']['width_in_chars']
left_col_width_chars = json_data['picky_py_config']['left_column']['width_in_chars']
announce_prog = json_data['picky_py_config']['header']['program_announce'] + ' ' + DEF_version
announce_file = json_data['picky_py_config']['left_column']['file_select_button']['announce_file']
announce_no_file = json_data['picky_py_config']['left_column']['file_select_button']['announce_no_file']

Python_version = 'Python:'+sg.sys.version
System_info = 'System:'+runningon.platform()
Uname = 'System:'+sprint(runningon.uname())
PySimpleGui_source = 'PySimpleGui source:'+sprint(sg)
PySimpleGui_version = 'PySimpleGui version:'+sg.ver
TCL_version ='TCL version:'+sg.tclversion_detailed
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
	last_resort_log.exception('Fatal error - cannot open '+user_log_file)
picky_py_logger.write('\n\n\n\nNew session at '+time.strftime("%d/%m/%Y %H:%M")+' of '+announce_prog)
picky_py_logger.write('\nUser '+current_user+' is logged on')
picky_py_logger.write('\nSystem:'+runningon.platform())
picky_py_logger.write('\nPython:'+sg.sys.version)
picky_py_logger.write('\nPySimpleGui version:'+sg.ver)
picky_py_logger.write('\nPySimpleGui source:'+sprint(sg))
picky_py_logger.write('\nTCL version:'+sg.tclversion_detailed)

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
next_log_str = ''
skipped_log = False
skipped_count = 0
def log_event(event_string):
    global skipped_log,skipped_count,previous_log_str
    if event_string != previous_log_str :
        if skipped_log :
            picky_py_logger.write('\n'+time.strftime("%d/%m/%Y %H:%M")+previous_log_str+' repeated '+str(skipped_count)+' times')
            skipped_log = False
            skipped_count = 0
        window['-REPORT-'].print(time.strftime("%d/%m/%Y %H:%M")+event_string)
        picky_py_logger.write('\n'+time.strftime("%d/%m/%Y %H:%M")+event_string)
        previous_log_str = event_string
    else:
        skipped_log = True
        skipped_count += 1
#programmer_command must only be called either the first time through the program OR after
#  test_command_fini has reported that the command is finished.
def programmer_command(event_string,command):
    global results,errors,process,statewindow
#    statewindow.check(True) #True forces cancel if not critical
#   log_event(event_string)
   # window['-FILE-'].update(disabled = True)
   # statewindow.message('Uploading,\ndo not unplug chip',True,False)
    ##spawn process.
    results = open(result_file_path, "w")
    errors  = open(error_file_path,"w")
    #command_id = 'main_directory_path+'/pk2cmd-x86_64.AppImage  -P'+DEVICE_NAME+' -I'
    # main_directory_path+'/pk2cmd-x86_64.AppImage  -PPIC16F15214 -M -F'+upload_path+'/pic16F15214_release_1_0.X.production.hex
    #command = 'nrfutil dfu usb-serial -pkg '+chosen_hex_file+' -p '+port_to_program.device+' -b 115200'
    #print('command=',command)
    try:
        process = subprocess.Popen(
            shlex.split(command), shell=False, stdout=results, stderr=errors)
    except:
        picky_py_logger.write("\nERROR {} while running {}".format(sys.exc_info()[1], command))
        exit('unable to spawn subprocess')


def test_command_fini(event_string):
    global results,errors,process
    success = True
    finished = process.poll() is not None
    if finished: #then the process has finished.
        results.close()
        errors.close()
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
                thisdict[dinfo["item"]] = dinfo["info"]
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
    
    

if some_failure or fail_list:
    if fail_list:
        picky_py_logger.write('\nModules failed to load='+fail_list)
    last_resort_log.critical('Fatal error - file problem, see '+user_log_file)
    exit(0)
if len(upload_files) == 1:
    #there is only one choice so use it.
    chosen_hex_file = upload_files[0]
    browse_button_text = announce_file.replace('***',os.path.basename(chosen_hex_file)) #replace *** with file name.
    browse_button_color = 'white on green'
else: 
    browse_button_text = announce_no_file
    browse_button_color = 'white on grey'

prog_announce_text = json_data['picky_py_config']['header']['program_announce']
left_column_font = tuple(json_data['picky_py_config']['left_column']['font'])
right_column_font = tuple(json_data['picky_py_config']['right_column']['font'])
right_column_header_text = json_data['picky_py_config']['right_column']['header_text']
# Column layout 
layout = [sg.vtop(
         [sg.Col([
                  [sg.FileBrowse(file_types=((announce_no_file, '*.'+DEF_upload_ext),),button_text = browse_button_text,
                     initial_folder = upload_path,tooltip = 'If there is only one file, it will be shown here.\n otherwise you need to choose.\
\nFiles can only be selected when not uploading and not in Auto', enable_events = True,
                     size=(left_col_width_chars,4),font=left_column_font,button_color=browse_button_color,key = '-FILE-',disabled=False, auto_size_button=True)],
                  [sg.Button('searching for\nchip',size=(left_col_width_chars,4),font=left_column_font,button_color='white on orange',key = '-ACTION-',disabled=True,
                  tooltip = 'When green push to program the chip.\nDo not unplug chip until told')],
                  [sg.Button('Auto is off',          size=(left_col_width_chars,5),font=left_column_font,button_color='white on red', key = '-AUTO-',
                  tooltip = 'If AUTO is on then any chip found\n will be immediately programmed.')],
                  [sg.Text('         ',             size=(left_col_width_chars+1,3),font=left_column_font,key='-STATE-')],
                  [sg.Button('Exit', key='-E-',tooltip = 'Exit the program, ALWAYS exit this way', font = left_column_font,  size=(left_col_width_chars,2))]
                 ]
                ) #from layout helper funcs. Vtop align tops of [elements]
         ,sg.Col([
                  [sg.Multiline(right_column_header_text,justification='center', size =(right_col_width_chars,2),write_only = True, background_color = 'light blue', font = right_column_font)],
                  [sg.Multiline(prog_announce_text+DEF_version+'\n',autoscroll = True,size = (right_col_width_chars, 
                     json_data['picky_py_config']['right_column']['number_of_lines']),font = right_column_font,
                  key='-REPORT-',auto_refresh = True,write_only = True,tooltip = 'Report on activity. No user input here.')],
                  ],expand_x = True)]
         )
         ]

# Display the window and get values
window = sg.Window(announce_prog, layout = layout, resizable = True, margins=(0,0), element_padding=(0,0),finalize=True)
(old_width,old_height) = window.size
awaiting_chip_plugin = True
statewindow = messagey('-STATE-','',5.5) #set up the message window with blank entry and 5.5 seconds timeout.
window['-REPORT-'].print(Python_version)
window['-REPORT-'].print(System_info)
#window['-REPORT-'].print(Uname+'\n')
window['-REPORT-'].print(PySimpleGui_version)
#window['-REPORT-'].print(PySimpleGui_source)
window['-REPORT-'].print(TCL_version)
log_event('User '+current_user+' is logged on\n')



#def choose_first_chip(list_of_ports):
class pro_state(Enum):
    Pickit_missing = 1
    pickit_inuse = 2
    awaiting_no_chip = 3
    pickit_available = 4
    pic16_available = 5
    awaiting_good_chip = 6

class prog_state:
    def __init__(self,atthemoment,before):
        self.now = atthemoment
        self.prev = before
    def change_to(self, new_state):
        print('changing state from',self.now,' to ',new_state)
        self.now = new_state
    def current_state():
        return now
    def now_is(self,test):
        return self.now == test
state_of_prog = prog_state(pro_state.Pickit_missing,pro_state.Pickit_missing)

#state_of_prog.change_to(pro_state.pickit_available)

#print(state_of_prog.now,state_of_prog.prev)
#print(state_of_prog.now_is(pro_state.pickit_available))
#exit(0)

    
    
    
    
    
    
programmer_state = '' # should be Pickit_missing, pickit_available, pickit_awaiting_off, pickit_inuse, pic16_available,
#  pick16_available - start programming. transition to pickit_inuse
#                    upload finished, transition from pickit_inuse to pickit_awaiting_off, start timer
#                   if pickit_awaiting_off then check for chip present. if no chip present  transition to pickit_available. Cancel timeout.
#                   if pickit_available then check for chip present. if present then to pick16_available.
def change_prog_state(new_state):
    global programmer_state
    old_state = programmer_state
    print('changing state from',programmer_state,' to ',new_state)
    programmer_state = new_state
change_prog_state("Pickit_missing")
#
#Define the command outside of the main loop, just to avoid constantly re-creating it.
# Should the user change the file name, it will be re-generated correctly in that event handler.
pk2cmd_program_chip = main_directory_path+'/pk2cmd-x86_64.AppImage  -P'+DEVICE_NAME+' -M -F'+chosen_hex_file

while True:
    if exit_requested and programmer_state != "pickit_inuse": #then tidy up and leave
        break
    else:
        if exit_requested:     window['-E-'].update(text='Still uploading, please wait')
    missed_event = True
    event, values = window.read(timeout = 500,timeout_key = "-TIMEOUT-",close = False)
    
    
    
    if event == '-ACTION-' and programmer_state == "pic16_available" :
        if not auto_upload : ##should not be an action event anyway if auto is set.
            window['-ACTION-'].update('uploading to chip',disabled=True,button_color='white on black')
            #pk2cmd_program_chip = main_directory_path+'/pk2cmd-x86_64.AppImage  -P'+DEVICE_NAME+' -M -F'+chosen_hex_file
            programmer_command(' Started manual upload', pk2cmd_program_chip) #start uploading process here.
            log_event(' Started manual upload')
            window['-FILE-'].update(disabled = True)
            statewindow.message('Uploading,\ndo not unplug chip',True,False)
            change_prog_state("pickit_inuse")
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
                if programmer_state != 'pickit_inuse':
                    window['-FILE-'].update(disabled = False,button_color = 'white on green')
                if programmer_state == "pic16_available":
                    window['-ACTION-'].update(disabled=False)
            window['-AUTO-'].update(text='AUTO is ON\n all inserted chips\nwill be programmed'
               if auto_upload else 'AUTO is OFF\npush button above\nto programme', button_color='white on green' if auto_upload else 'white on red')
        missed_event = False
        
        
    if event == '-FILE-':
        temp_file = values['-FILE-']
        if temp_file: #then there is a file string
            if temp_file != chosen_hex_file: #then it is different
                log_event('Changed upload file to '+temp_file)
                chosen_hex_file = temp_file
                pk2cmd_program_chip = main_directory_path+'/pk2cmd-x86_64.AppImage  -P'+DEVICE_NAME+' -M -F'+chosen_hex_file # replace command
                window['-FILE-'].update(announce_file.replace('***',os.path.basename(chosen_hex_file)), button_color = 'white on green')
                if programmer_state == "pic16_available":
                    window['-ACTION-'].update(disabled=False)
        missed_event = False
    if event == "-TIMEOUT-":
        if programmer_state == "pickit_awaiting_off":
            programmer_command('checking for no chip',pk2cmd_what_chip)
            log_event(' Checking for chip removed')
            change_prog_state("awaiting_no_chip")
        if programmer_state == "awaiting_no_chip":
            #show('second show')
            proc_terminated = test_command_fini('')
            if proc_terminated[0]:
                if parse_file_regex(result_file_path, regex)["Device Name"] == "<no device>":
                    #then the user has removed the programmed chip.
                    change_prog_state("pickit_available")
                #otherwise no change.
        if programmer_state == "awaiting_good_chip":
            proc_terminated = test_command_fini('')
            if proc_terminated[0]:
                print(result_file_path,parse_file_regex(result_file_path, regex))
                if parse_file_regex(result_file_path, regex)["Device Name"] == DEVICE_NAME :
                    print('found '+DEVICE_NAME)
                    change_prog_state('pic16_available')
                    window['-ACTION-'].update(disabled=False)
                else:
                    change_prog_state("pickit_available") #go and test again
        if programmer_state == "Pickit_missing":
            #then try to find 
            pickits = []
            get_list_pickit3(pickits)
            if len(pickits) == 1:
                #show('early show')
                #then there is a single Pickit installed. Record the info and set the state.
                current_pickit = pickits[0]
                change_prog_state("pickit_available")
                statewindow.message(current_pickit.product+'\ndetected, serial=\n'+current_pickit.serial+'\n',True,False)
                log_event("Programmer: "+current_pickit.name+current_pickit.product+"with serial= "+current_pickit.serial)
            else:
                statewindow.message('More than one\nprogrammer detected\nonly 1 permitted',True,False)
                for programmer in pickits:
                    log_event("Programmer:"+programmer.name+programmer.product+" with serial="+programmer.serial)
        missed_event = False
        # next line removes timed out messages.
        ########statewindow.check(not awaiting_chip_plugin and not_uploading) #cancel if not awaiting chip plugin and not uploading
        if auto_upload and programmer_state == "pic16_available":
            programmer_command(' Started auto upload', pk2cmd_program_chip) #start uploading process here.
            log_event(' Started auto upload')
            window['-ACTION-'].update('uploading to chip\n',disabled=True,button_color='white on black')
            window['-FILE-'].update(disabled = True)
            statewindow.message('Uploading,\ndo not unplug chip',True,False)
            change_prog_state("pickit_inuse")
        elif programmer_state == "pickit_inuse":
            results = test_command_fini(' ')
            if results[0]: #Just finished uploading, change state to awaiting chip change
                programmer_state = "pickit_awaiting_off"
                window['-ACTION-'].update('awaiting chip\nremoval',button_color='white on orange',disabled=True)
                if results[1]: #then all is well.
                    statewindow.message('Finished uploading\nunplug now',True,False)
                    msg=' Successful upload to '
                else:
                    #perhaps parse and report error here.
                    msg=' Failed upload'
                    statewindow.message('Failed uploading\nunplug now',True,True)
                log_event(msg+str)
                if not auto_upload:
                    window['-FILE-'].update(disabled = False)

        if programmer_state == "pickit_available":
            #then check for correct chip available
            programmer_command('Seeking '+DEVICE_NAME+' to programme',pk2cmd_what_chip)
            log_event(' Seeking '+DEVICE_NAME+' to programme')
            change_prog_state("awaiting_good_chip")
    if event == "-E-" or event == sg.WIN_CLOSED or event == sg.WIN_CLOSED or event == 'Exit':
        exit_requested = True #only abandon if the upload is finished.
        missed_event = False
    if missed_event:
        print('\nMissed event=',event, values)
log_event('Exited gracefully')
#picky_py_logger.write('\nExited gracefully at '+time.strftime("%d/%m/%Y %H:%M")+'\n\n\n')
picky_py_logger.close()
window.close()

#print('~\working\\'+datetime.datetime.now().time.strftime("%y%m%d_%H%M%S")+'_'+str(uuid.uuid4().hex)+'.usbres')
