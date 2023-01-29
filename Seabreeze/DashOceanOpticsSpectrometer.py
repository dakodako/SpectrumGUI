#%%
import random
import numpy 

import dash_daq as daq
# import dash_html_components as html 
# import dash_core_components as dcc 
from dash import Dash, dcc, html, Input, Output

try:
    import seabreeze.spectrometers as sb 
    from seabreeze.spectrometers import SeaBreezeError 
except Exception as e:
    print(e)

class DashOceanOpticsSpectrometers:
    def __init__(self, specLock, commLock):
        self._spec = None
        self._specmodel = ''
        self._lightSources = {}
        self._spectraData = [[],[]]
        self._controlFunctions = {}
        self._int_time_max = 650000000
        self._int_time_min = 1000
        self.comm_lock = commLock
        self.spec_lock = specLock
    
    def assign_spec(self):
        return

    def get_spectrum(self):
        return self._spectraData
    
    def send_control_values(self, commands):
        return ({},{})
    
    def send_light_intensity(self, val):
        return 

    def model(self):
        return self._specmodel
    
    def light_sources(self):
        return self._lightSources
    
    def int_time_max(self):
        return self._int_time_max
    
    def int_time_min(self):
        return self._int_time_min

class PhysicalSpectrometer(DashOceanOpticsSpectrometers):

    def __init__(self, specLock, commLock):
        super().__init__(specLock, commLock)
        try:
            self.spec_lock.acquire()
            print('init assign spec')
            self.assign_spec()
        except SeaBreezeError:
            pass 
        finally:
            self.spec_lock.release()
        self._controlFunctions = {
            'integration-time-input':
            "self._spec.integration_time_micros",

            'nscans-to-average-input':
            "self._spec.continuous_strobe_set_enable",

            'continuous-strobe-toggle-input':
            "self._spec.continuous_strobe_set_enable",

            'continuous-strobe-period-input':
            "self._spec.continuous_strobe_set_period_micros",

            'light-source-input':
            "self.update_light_source"
        }
    
    def assign_spec(self):
        try:
            self.comm_lock.acquire()
            devices = sb.list_devices()
            self._spec = sb.Spectrometer(devices[0])
            print(self._spec)
            self._specmodel = self._spec.model 
            # self._lightSources = [{'label': ls.__repr__(), 'value': ls}
                                #   for ls in list(self._spec.light_sources())]
            # self._int_time_min = self._spec.minimum_integration_time_micros()
        except Exception as e:
            print("assign spec error")
            print(e)
            pass 
        finally:
            self.comm_lock.release()
    def get_spectrum(self):
        if self._spec is None:
            try:
                self.spec_lock.acquire()
                print('get spectrum assign spec')
                self.assign_spec()
            except Exception as e:
                print('get spectrum error')
                print(e)
            finally:
                self.spec_lock.release()
        try:
            self.comm_lock.acquire()
            self._spectraData = self._spec.spectrum(correct_dark_counts=True,
                                                    correct_nonlinearity=True)
        except Exception:
            pass
        finally:
            self.comm_lock.release()
        
        return self._spectraData