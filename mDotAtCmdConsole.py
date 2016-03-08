from __future__ import print_function
import serial
from time  import sleep
from serial.tools import list_ports
import sys
import distutils.util

APP_EUI = "00:25:0C:00:00:01:00:01"


class AT_Console:


    def __init__(self, port=None):
        self.serialPort   = None
        self.readTimeout  = 10 
        self.writeTimeout = 5
        self.port = port
        self.verbose = False
        self.device = None
        self.baudrate  = 115200
        self.appKey    = None
        self.appEui    = None
        self.prompt    = ">>"
        self.history   = []
        self.commands  =  { "quit":self.quit, 
                            "loop":self.loop, 
                            "join":self.join,
                            "appKey":self.appKeyPrompt,
                            "history":self.displayHistory}


    def getPort(self, port):
            ports = serial.tools.list_ports.grep(port) 
            if len(ports) == 1:
                return  ports[0].device
            else:
                return None

    def selectPort(self):

        ports = list_ports.comports()

        if len(ports) == 0:
            return

        if len(ports) == 1: 
            self.port = ports[0].device 
        else:
            # List ports
            for i,p in enumerate(ports):
                print(i,p)
            # Select port
            while True: 
                portIndex = raw_input("Select port index: ")
                if portIndex.isdigit():
                    portIndex = int(portIndex)
                    if portIndex < len(ports):
                        self.port = ports[portIndex].device 
                        break

    def getSerialPort(self): 

        if self.port is not None:
            self.port = self.getPort(self.port)

        if self.port is None:
            self.selectPort()

    def start(self):
        self.getSerialPort()

        print("Searching for mDot serial port......", end='')
        print("[{}]".format(self.port))
        if self.port is None:
            return False 

        print("Opening port........................"
                .format(self.port),end='')
        self.serialPort = serial.serial_for_url(
                self.port,write_timeout=self.writeTimeout, timeout=self.readTimeout,baudrate=self.baudrate) 

        if self.serialPort is None:
            print("[ERROR]")
            return 
        else:
            print("[OK]")

        for i in range(0,3):
            print("Checking AT command response........",end='')
            result = self.command("AT+DI",False)
            print("[{}]".format(result[0]))
            if result[0] == 'OK':
                for line in result[1]:
                    if len(line.split(":")) == 8 or len(line.split("-")) == 8:
                        self.device = line
                print("Connected to mDot...................[{}]".format(self.device))
                self.run()
                break
            else:
                sleep(1)

    def run(self):
        # reset command history
        self.history = []

        while True:
            try:
                command = raw_input("\r\n"+self.prompt)
                command = command.strip()
            except:
                print("\r\nExiting console")
                break 
            if len(command.strip()) > 0: 
                self.command(command)

        self.close();


    def close(self):
        if self.serialPort is not None:
            print("Closing {}".format(self.port))
            self.serialPort.close() 

    def command(self, cmd, echo=True):
        lines = [] 
        ok    = False
        result = None
        endCommandStrings = ['OK','ERROR']

        if cmd != 'history':
            self.history.append(cmd)

        if cmd in self.commands: 
            self.commands[cmd]();
        else:
            try:
                self.serialPort.write(cmd + '\r\n')
            except:
                return lines 

            while True:
                # Read line
                try:
                    line = self.serialPort.readline()
                except serial.SerialException as e:
                    print("Serial port error: {}".format(e.message))


                # End of output
                if len(line) == 0:
                    break

                line = line.strip()

                # echo line
                if echo is True:
                    print(line.strip())
                lines.append(line)

                # Is this the last line
                if line.strip() in endCommandStrings:
                    result = line
                    break
            return (result,lines)

    def normalizeAppKey(self, key):
        appKey = None
        for separator in [',',' ','.']:
            tokens = key.split(separator)
            if len(tokens) == 16:
                appKey = ".".join([format(int(x,16),'02x') for x in tokens])
                break
        return appKey

    def appKeyPrompt(self):
        # prompt for key 
        appKey = raw_input("Application Key (from Senet Developer Portal): ")
        # normalize key
        self.appKey = self.normalizeAppKey(appKey)

    def appEuiPrompt(self):
        self.appEui = raw_input("Application Identifier (e.g. 00250C0100010001): ")

    def getAppKey(self):
        return self.appKey 

    def join(self):
        DEMO_AT_CMD_DELAY = 2

        #Turn on mDot debug logging
        self.command('AT+LOG=6')


        # Reset to factory defaults 
        print("----Reset mDot to factory defaults")
        self.command('AT&F', True)
        sleep(DEMO_AT_CMD_DELAY)

        # Set Public network
        print("\r\n----Set Public Network") 
        self.command('AT+PN=1', True)
        sleep(DEMO_AT_CMD_DELAY)

        # Channel support
        print("\r\n----Set Channel Support") 
        self.command('AT+FSB=0', True)
        sleep(DEMO_AT_CMD_DELAY)

        # App EUI  
        print("\r\n----Set Application EUI") 
        self.command('AT+NI=0,'+APP_EUI, True)
        sleep(DEMO_AT_CMD_DELAY)

        # Set Application Key 
        print("\r\n----Set Application Key") 
        appKeyOk = False
        if self.getAppKey() is not None:
            result = self.command('AT+NK=0,'+self.getAppKey(), True) 
            appKeyOk = result[0] == 'OK'
            if appKeyOk is True:
                sleep(DEMO_AT_CMD_DELAY)

        while appKeyOk is False:
            self.appKeyPrompt()
            result = self.command('AT+NK=0,'+self.getAppKey(), True) 
            appKeyOk = result[0] == 'OK'
        sleep(DEMO_AT_CMD_DELAY)

        # OTA Join mode
        print("\r\n----Set Over The Air (OTA) Join mode") 
        self.command('AT+NJM=1', True)
        sleep(DEMO_AT_CMD_DELAY)

        # LSB Byte order
        print("\r\n----Send EUIs in LSB order") 
        self.command('AT+JBO=0', True)
        sleep(DEMO_AT_CMD_DELAY)

        # Transmit power
        print("\r\n----Set Transmit power") 
        self.command('AT+TXP=20')

        # Datarate 
        print("\r\n----Set Datarate") 
        self.command('AT+TXDR=10')

        #ADR
        print("\r\n----Enable ADR") 
        self.command('AT+ADR=1')

        # Save configuration
        print("\r\n----Save configuration") 
        self.command('AT&W')
        sleep(DEMO_AT_CMD_DELAY)

        # Join network
        joined = False
        print("\r\n----Join Network") 
        delay = 5
        for i in range(0, 24):
            result = self.command('AT+JOIN')
            joined = result[0] == 'OK'
            if joined is True:
                break
            else:
                print("Delaying {} seconds before next join attempt".format(delay))
                sleep(delay)
     
        if joined is False:
            return

        print("\r\n----Set Channel Support, Again...") 
        self.command('AT+FSB=0', True)
        sleep(DEMO_AT_CMD_DELAY)

        # Send data
        print("\r\n----Transmit uplink") 
        self.command('AT+SEND HelloWorld!')


    def demo(self):
        commands = {('AT+PN',   'HELP'),
                    ('AT+FSB'   'HELP'),
                    ('AT+NI',   'HELP'),
                    ('AT+NK',   'HELP'),
                    ('AT+TXDR', 'HELP'),
                    ('AT+TXP',  'HELP'),
                    ('AT+ADR',  'HELP'),
                    ('AT+JOIN',  'HELP')}

        # self.command('AT+PN=1', True)
        # self.command('AT+TXP=20')
        # self.command('AT+TXDR=10')
        # self.command('AT+ADR=1')
        # self.command('AT+FSB=0', True)
        # self.command('AT+NI=0,'+APP_EUI, True)
        # self.command('AT+JOIN')

        self.command('AT&F') 
        self.command('AT+JBO=0')
        self.command('AT+LOG=6')

        # Get Application Key
        self.appKey = None
        while self.appKey is False:
            self.appKeyPrompt()

        # Get Application EUI
        self.appEuiPrompt()

        # result = self.command('AT+NK=0,'+self.getAppKey(), True) 

        for command in commands:
            self.interactiveCommand(command)

        self.command('AT&W')

        # Join network

    def loop(self):
        commands = []
        delay    = 0
        count    = -1

        # Get commands to loop on
        while True:
            command = raw_input("Enter command or 'start' to begin loop: ")
            command = command.strip()
            if command == 'start':
                break
            elif command.startswith('delay'):
                delay = int(filter(str.isdigit,command))
            elif command.startswith('count'):
                count =  int(filter(str.isdigit,command))
            else:
                commands.append(command) 

        # No commands entered
        if len(commands) == 0:
            return

        if count > 0:
            print("Starting loop count {}".format(count))
            for i in range(0,count):
                try:
                    for command in commands:
                        self.command(command)
                    if delay > 0:
                        sleep(delay)
                except:
                    return
        else:
            while True:
                try:
                    for command in commands:
                        self.command(command)
                    if delay > 0:
                        print("sleep({})".format(delay))
                        sleep(delay)
                except:
                    return
 
    def quit(self): 
        print("Exiting")
        self.close()
        exit()

    def displayHistory(self):
        for i,c in enumerate(self.history,1):
            print("[{}] {}".format(i,c))


if __name__ == '__main__':
    console = AT_Console()
    console.start()
