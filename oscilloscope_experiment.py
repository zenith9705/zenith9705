#THIS WORK IS WRITTEN BY CELINE L FOR DUTTLAB. CONTACT ZRL24@PITT.EDU FOR ANY INQUIRIES. 


from Controller.oscilloscope import grab_frequencies
from src.core import Parameter, Experiment, Device
from src.Controller.oscilloscope import Oscilloscope
from time import sleep
import pyqtgraph as pg
import numpy as np


class OscilloscopeExperiment(Experiment):
    """
    Waveform measurement experiment using the Agilent InfiniiVision MSO7104A oscilloscope.
    Acquires and displays live waveform data from up to four channels.
    """

    _DEFAULT_SETTINGS = [
        Parameter('channel1_enabled', False, bool, 'Enable channel 1'),
        Parameter('channel2_enabled', False, bool, 'Enable channel 2'),
        Parameter('channel3_enabled', False, bool, 'Enable channel 3'),
        Parameter('channel4_enabled', False, bool, 'Enable channel 4'),
        Parameter('trigger_source', 0, int, 'Trigger source channel (0-3)'),
        Parameter('trigger_level', 0.0, float, 'Trigger level in volts'),
        Parameter('fft_check',False,bool,"Indicates FFT Function"),
        Parameter('num_acquisitions', 1, int, 'Number of waveforms to acquire (1 = single shot)'),
    ]

    # Links the string key 'oscilloscope' to the Oscilloscope device class.
    # The GUI and load_and_append() use this to know which device this
    # experiment needs and to create it if it doesn't already exist.
    _DEVICES = {'oscilloscope': 'oscilloscope'}

    # No sub-experiments needed
    _EXPERIMENTS = {}

    def __init__(self, devices, experiments=None, name=None, settings=None,
                 log_function=None, data_path=None):
        # Note: the base Experiment class expects 'sub_experiments', not 'experiments'
        super().__init__(name, settings=settings, sub_experiments=experiments,
                         devices=devices, log_function=log_function,
                         data_path=data_path)

        # Grab the oscilloscope instance from the devices dictionary.
        # devices['oscilloscope'] is a dict of the form
        # {'instance': <Oscilloscope>, 'settings': <Parameter>}
        # as set up by Experiment.load_and_append()
        self.scope = self.devices['oscilloscope']['instance']

    def _function(self):
        """
        Main experiment body. Called by run() on the experiment thread.
        Pushes current settings to the oscilloscope, acquires waveforms,
        stores them in self.data, and signals the GUI to plot.
        """
        # --- Push GUI settings to the oscilloscope hardware ---
        self.scope.update({
            'channel1_enabled': self.settings['channel1_enabled'],
            'channel2_enabled': self.settings['channel2_enabled'],
            'channel3_enabled': self.settings['channel3_enabled'],
            'channel4_enabled': self.settings['channel4_enabled'],
            'fft_check':self.settings['fft_check'],
            'trigger_source':   self.settings['trigger_source'],
            'trigger_level':    self.settings['trigger_level']
        })

        # Initialize data storage. Each channel gets x (time) and y (voltage)
        # lists. They start empty and are filled only if the channel is enabled.
        self.data = {
            'x1': [], 'y1': [],
            'x2': [], 'y2': [],
            'x3': [], 'y3': [],
            'x4': [], 'y4': [],
            'frequencies': [], 'amplitudes': []
        }

        self.log("Starting continuous acquisition, press stop to end.")

        while not self._abort:

            # get_data() returns eight lists: x1,y1,x2,y2,x3,y3,x4,y4
            # Empty lists are returned for disabled channels
            x1, y1, x2, y2, x3, y3, x4, y4 = self.scope.get_data()
            frequencies, amplitudes = grab_frequencies(self.scope,source_channel=self.scope.instr._get_trigger_source())

            # Only store data for enabled channels
            if self.settings['channel1_enabled']:
                self.data['x1'] = x1
                self.data['y1'] = y1
            if self.settings['channel2_enabled']:
                self.data['x2'] = x2
                self.data['y2'] = y2
            if self.settings['channel3_enabled']:
                self.data['x3'] = x3
                self.data['y3'] = y3
            if self.settings['channel4_enabled']:
                self.data['x4'] = x4
                self.data['y4'] = y4
            if self.settings['fft_check']:
                self.data['frequencies'] = frequencies
                self.data['amplitudes'] = amplitudes
            # Report progress to the GUI as a percentage.
            # This also triggers _plot() to be called via updateProgress signal.
            self.progress = 50
            self.updateProgress.emit(self.progress)

            # Small delay between acquisitions to avoid flooding the instrument
            sleep(0.1)

        self.log("Acquisition complete.")

    def _plot(self, axes_list):
        """
        Plots waveform data onto the provided pyqtgraph axes.
        Called by the GUI whenever updateProgress is emitted and when
        the experiment finishes.

        axes_list[0] is the main plot area (bottom widget in GUI).
        """
        ax = axes_list[0]
        ax_fft = axes_list[1]
        ax.clear()
        ax_fft.clear()

        # Channel colors match typical oscilloscope convention
        colors = {
            'ch1': (255, 255,   0),   # yellow
            'ch2': (  0, 255,   0),   # green
            'ch3': (  0, 128, 255),   # blue
            'ch4': (255,   0,   0),   # red
            'fft': ( 180, 0, 255)
        }

        plotted_any = False

        if self.settings['channel1_enabled'] and len(self.data.get('x1', [])) > 0:
            ax.plot(self.data['x1'], self.data['y1'],
                    pen=pg.mkPen(color=colors['ch1'], width=1),
                    name='Ch1')
            plotted_any = True

        if self.settings['channel2_enabled'] and len(self.data.get('x2', [])) > 0:
            ax.plot(self.data['x2'], self.data['y2'],
                    pen=pg.mkPen(color=colors['ch2'], width=1),
                    name='Ch2')
            plotted_any = True

        if self.settings['channel3_enabled'] and len(self.data.get('x3', [])) > 0:
            ax.plot(self.data['x3'], self.data['y3'],
                    pen=pg.mkPen(color=colors['ch3'], width=1),
                    name='Ch3')
            plotted_any = True

        if self.settings['channel4_enabled'] and len(self.data.get('x4', [])) > 0:
            ax.plot(self.data['x4'], self.data['y4'],
                    pen=pg.mkPen(color=colors['ch4'], width=1),
                    name='Ch4')
            plotted_any = True

        if self.settings['fft_check'] and len(self.data.get('frequencies', [])) > 0:
            ax_fft.plot(self.data['frequencies'],self.data['amplitudes'],pen=pg.mkPen(color=colors['fft'], width=1),name='FFT')
            plotted_any = True

        if plotted_any:
            ax.setLabel('left', 'Voltage', units='V')
            ax.setLabel('bottom', 'Time', units='s')
            ax.setTitle('Oscilloscope Waveforms')
            ax.showGrid(x=True, y=True)
            ax.addLegend()
            ax_fft.setLabel('bottom', 'Amplitude', units='dBV')
            ax_fft.setLabel('left', 'Frequency', units='Hz')
            ax_fft.setTitle('FFT Waveform')
            ax_fft.showGrid(x=True, y=True)

        else:
            # No enabled channels with data — show a message
            ax.setTitle('No channels enabled or no data acquired yet')

        ax.addLegend()
        ax_fft.addLegend()


    def _update_plot(self, axes_list):
        """
        Called during acquisition to refresh the plot without clearing axes.
        For waveforms, a full redraw is cheap enough that we just call _plot().
        """
        self._plot(axes_list)

    def _update(self, axes_list):
        """
        Called during acquisition to refresh the plot without clearing axes.
        For waveforms, a full redraw is cheap enough that we just call _plot().
        """
        self._plot(axes_list)

    def get_axes_layout(self, figure_list):
        """
        Tells the GUI which axes objects to use for plotting.
        We only need one plot area (the main bottom widget).
        """
        axes_list = []
        if self._plot_refresh:
            figure_list[0].clear()
            figure_list[1].clear()
            axes_list.append(figure_list[0].addPlot(row=0, col=0))
            axes_list.append(figure_list[1].addPlot(row=0, col=0))
        else:
            axes_list.append(figure_list[0].getItem(row=0, col=0))
            axes_list.append(figure_list[1].getItem(row=0, col=0))
        return axes_list
