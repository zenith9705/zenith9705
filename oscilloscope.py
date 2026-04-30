#THIS WORK IS WRITTEN BY CELINE L FOR DUTTLAB. CONTACT ZRL24@PITT.EDU FOR ANY INQUIRIES. 

import matplotlib
#matplotlib.use('TkAgg') #--> SUPER IMPORTANT
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import vxi11
import ivi
import numpy as np
from src.core import Device, Parameter

fig, ax = plt.subplots() #For live plots

class Oscilloscope(Device):
    '''
    Oscilloscope Device
    an implementation of an oscilloscope
    '''

    '''
    Default settings that all oscilloscope objects have
    '''
    _DEFAULT_SETTINGS = Parameter([
        Parameter('ip_address','192.168.2.183'),
        #Parameter('instr'),
        Parameter('channel1_enabled',False,bool),
        Parameter('channel2_enabled', False, bool),
        Parameter('channel3_enabled', False, bool),
        Parameter('channel4_enabled', False, bool),
        Parameter('fft_check',False,bool,"Indicates FFT Function"),
        Parameter('trigger_level',0.0, float),
        Parameter('trigger_source',1,int)
         ]
    )


    '''
    init - connects to oscilloscope and runs initial update function
    '''
    def __init__(self, name=None, settings=None):
        ip = (settings or {}).get('ip_address', '192.168.2.183')
        try:
            self.instr = ivi.agilent.agilentMSO7104A(f"TCPIP::{ip}::INSTR")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to oscilloscope at {ip}: {e}")

        # Now it's safe to call super().__init__(), which will call update(settings)
        super(Oscilloscope, self).__init__(name, settings)

    '''
    connect - connects to oscilloscope
    '''
    def is_connected(self):
        ip = self.settings['ip_address']
        instr = vxi11.Instrument(ip)
        idn = instr.ask("*IDN?")
        print(f"Connected to {idn}")

    '''
    update - user updates internal values
    '''
    def update(self, settings=None):
        # Guard: if instr isn't ready yet, just update the settings dict and return
        if not hasattr(self, 'instr') or self.instr is None:
            if settings:
                super().update(settings)
            return

        # Let the base class update self._settings first
        if settings:
            super().update(settings)

       #Update channels on and off
        self.instr._set_channel_enabled(0,self.settings['channel1_enabled'])
        self.instr._set_channel_enabled(1,self.settings['channel2_enabled'])
        self.instr._set_channel_enabled(2,self.settings['channel3_enabled'])
        self.instr._set_channel_enabled(3,self.settings['channel4_enabled'])

        #Update trigger source
        if self.settings['trigger_source'] >=0 or self.settings['trigger_source'] <= 3:
            source = "channel"+str(int(self.settings['trigger_source'])+1)
            try:
                self.instr._set_trigger_source(source)
            except(IndexError):
                print('Trigger source must be an integer between 0 and 3.')

        #Updates trigger_level
        #Trigger_level must be between -0.5channel_range and 0.5channel_range
        sourcen = self.instr._get_trigger_source()
        source_map = {"channel1": 0, "channel2": 1, "channel3": 2, "channel4": 3}
        source1 = source_map.get(sourcen, 0)
        channel_range = self.instr._get_channel_range(source1)
        trigger_level = self._settings['trigger_level']
        if (-0.5 * channel_range) <= trigger_level <= (0.5 * channel_range):
            try:
                self.instr._set_trigger_level(trigger_level)
            except IndexError:
                print('Trigger level is out of range.')

    '''
    read_probes - user retrieves internal values
    '''
    def read_probes(self, key=None):
        #track and verify key
        if key is None:
            # No argument: return all probe values as a dictionary
            return super().read_probes()

        assert key in self._PROBES

        #for each key, define a specific action and return a value
        #have a specific key for reading waveform, maybe go waveform by waveform
        if key == 'read_wave1':
            waveform1 = self.instr._measurement_read_waveform(0, 2)
            value = list(waveform1)
        elif key == 'read_wave2':
            waveform2 = self.instr._measurement_read_waveform(1, 2)
            value = list(waveform2)
        elif key == 'read_wave3':
            waveform3 = self.instr._measurement_read_waveform(2, 2)
            value = list(waveform3)
        elif key == 'read_wave4':
            waveform4 = self.instr._measurement_read_waveform(3, 2)
            value = list(waveform4)
        elif key == 'read_fft':
            value = list(grab_frequencies(self,source_channel=self.instr._get_trigger_source()))
        elif key == 'fft_check':
            value = True
            self.fft_check = value
        elif key == 'channel1_enabled':
            value = bool(self.instr._get_channel_enabled(0))
        elif key == 'channel2_enabled':
            value = bool(self.instr._get_channel_enabled(1))
        elif key == 'channel3_enabled':
            value = bool(self.instr._get_channel_enabled(2))
        elif key == 'channel4_enabled':
            value = bool(self.instr._get_channel_enabled(3))
        elif key == 'trigger_source':
            result = self.instr._get_trigger_source()
            raw = result[0] if isinstance(result, tuple) else result
            source_map = {'channel1': 0, 'channel2': 1, 'channel3': 2, 'channel4': 3}
            value = source_map.get(raw, 0)
        elif key == 'trigger_level':
            result = self.instr._get_trigger_level()
            raw = result[0] if isinstance(result, tuple) else result
            value = int(raw)  # returns a float, matching _DEFAULT_SETTINGS
        else:
            raise KeyError(f"Key '{key}' is in _PROBES but not handled in read_probes()")

        return value


    '''
    Establishes specific keys for the read_probes function
    '''
    @property
    def _PROBES(self):
        return {
        'read_wave1': 'Returns wave points (x,y) of channel1 wave',
        'read_wave2': 'Returns wave points (x,y) of channel2 wave',
        'read_wave3': 'Returns wave points (x,y) of channel3 wave',
        'read_wave4': 'Returns wave points (x,y) of channel4 wave',
        'fft': 'Returns fourier transform data',
        'fft_check': 'Indicates whether to retrieve or not',
        'channel1_enabled': 'Checks if channel1 is on',
        'channel2_enabled': 'Checks if channel2 is on',
        'channel3_enabled': 'Checks if channel3 is on',
        'channel4_enabled': 'Checks if channel4 is on',
        'trigger_source': 'Identifies trigger source',
        'trigger_level': 'Identifies trigger level'
        }


    '''
    get_data - fetches waveforms from oscilloscope
    '''
    def get_data(self):
        #declare variables as empty arrays beforehand
        x1=[]
        y1=[]
        x2=[]
        y2=[]
        x3=[]
        y3=[]
        x4=[]
        y4=[]
        ch1 = self.instr._get_channel_enabled(0)
        ch2 = self.instr._get_channel_enabled(1)
        ch3 = self.instr._get_channel_enabled(2)
        ch4 = self.instr._get_channel_enabled(3)

        #update arrays
        if ch1==True:
            waveform1 = self.instr._measurement_read_waveform(0, 2)
            x1 = [pt[0] for pt in waveform1]
            y1 = [pt[1] for pt in waveform1]
        if ch2 == True:
            waveform2 = self.instr._measurement_read_waveform(1, 2)
            x2 = [pt[0] for pt in waveform2]
            y2 = [pt[1] for pt in waveform2]
        if ch3 == True:
            waveform3 = self.instr._measurement_read_waveform(2, 2)
            x3 = [pt[0] for pt in waveform3]
            y3 = [pt[1] for pt in waveform3]
        if ch4 == True:
            waveform4 = self.instr._measurement_read_waveform(3, 2)
            x4 = [pt[0] for pt in waveform4]
            y4 = [pt[1] for pt in waveform4]

        return x1,y1,x2,y2,x3,y3,x4,y4

def query(self,cmd):
    """Send a command and return the response string."""
    return self.instr._ask(cmd).strip()

def grab_frequencies(self, source_channel, window='HANN'):
    self.instr._write(f":MATH:SOUR CHAN{source_channel}")  # set FFT source channel
    self.instr._write(":MATH:FUNC FFT")  # set math function to FFT
    self.instr._write(f":MATH:FFT:WIND {window}")  # set windowing function
    self.instr._write(":MATH:DISP ON")  # turn math display on
    print(f"FFT configured: source=CHAN{source_channel}, window={window}")
    """
        Read the FFT waveform data from the oscilloscope math channel.

        Returns:
            frequencies: numpy array of x-axis frequency values in Hz
            amplitudes:  numpy array of y-axis amplitude values in dBV
        """
    # Point the waveform source at the math (FFT) channel
    self.instr._write(":WAV:SOUR MATH")

    # Request raw byte data format for efficiency
    self.instr._write(":WAV:FORM BYTE")
    self.instr._write(":WAV:POIN:MODE RAW")
    # ── Read preamble ──────────────────────────────────────────────────
    # The preamble contains all the scaling information needed to convert
    # raw byte values into real frequency and amplitude values.
    # It returns 10 comma-separated values:
    #   [0] format    [1] type      [2] points    [3] count
    #   [4] x_incr    [5] x_origin  [6] x_ref
    #   [7] y_incr    [8] y_origin  [9] y_ref
    preamble = query(self, ":WAV:PRE?").split(',')

    num_points = int(preamble[2])
    x_increment = float(preamble[4])  # Hz per point
    x_origin = float(preamble[5])  # starting frequency in Hz
    x_reference = float(preamble[6])  # reference point index
    y_increment = float(preamble[7])  # dBV per count
    y_origin = float(preamble[8])  # dBV offset
    y_reference = float(preamble[9])  # reference count value

    print(f"Waveform info: {num_points} points, "
          f"freq range {x_origin:.1f} to "
          f"{x_origin + x_increment * num_points:.1f} Hz")

    # ── Read raw waveform bytes ────────────────────────────────────────
    # The oscilloscope returns data in IEEE 488.2 block format:
    # # <digits> <byte_count> <data bytes>
    # vxi11 handles the block header automatically and returns raw bytes.
    self.instr._write(":WAV:DATA?")
    raw = self.instr._read_raw()

    # More robust IEEE block header strip
    # Format: '#' + '1 digit N' + 'N digits of byte count' + data
    n_digits = int(chr(raw[1]))  # how many digits describe the byte count
    byte_count = int(raw[2:2 + n_digits])  # the actual byte count
    raw_data = raw[2 + n_digits:]  # everything after the header

    # Convert raw bytes to numpy array of unsigned integers
    raw_values = np.frombuffer(raw_data, dtype=np.uint8, count=num_points)

    # ── Scale raw values to real units ────────────────────────────────
    # Formula from the MSO7104A programmer's guide:
    # value = (raw - y_reference) * y_increment + y_origin
    amplitudes = (raw_values.astype(float) - y_reference) * y_increment + y_origin

    # Build frequency axis
    frequencies = x_origin + x_increment * (np.arange(num_points) - x_reference)

    return frequencies, amplitudes

if __name__ == '__main__':
    nd = Oscilloscope()
    nd.update()
    #nd.live_plot()
    print(nd.get_data())
