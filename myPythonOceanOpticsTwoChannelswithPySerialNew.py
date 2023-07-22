#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Didi Chi
"""
# import PyQt5

from PyQt5 import QtCore, QtWidgets,uic
from PyQt5.QtGui import * 
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from QLed import QLed
import winsound
# from qtwidgets import Toggle
# from threading import Thread
# from Light import Spectrometer as sb
import seabreeze.spectrometers as sb
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import pyqtSlot
from matplotlib.figure import Figure
import pyqtgraph as pg
from datetime import datetime
import serial
import serial.tools.list_ports
import traceback

import sys
import os
import time
import numpy as np
import queue

save_counter = 0

ports = list(serial.tools.list_ports.comports())
port = None
for p in ports:
    print(p.description)
    if "Arduino" in p.description:
        port = p[0]
    elif "Serial" in p.description:
        port = p[0]
    else:
        port = None

pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'k')

class SaveThread2(QtCore.QThread):
    startSaving = QtCore.pyqtSignal(str)
    setTotalProgress = QtCore.pyqtSignal(int)
    setCurrentProgress = QtCore.pyqtSignal(int)
    succeeded = QtCore.pyqtSignal()
    succeeded2 = QtCore.pyqtSignal(list, list)
    changeLineEdit2 = QtCore.pyqtSignal(str)
    # dataEReady = QtCore.pyqtSignal(list)
    # dataLReady = QtCore.pyqtSignal(list)
    finishOneMeasurement = QtCore.pyqtSignal()
    def __init__(self, spec, channelMode, serialComm, inteTime1,inteTime2, scans1,scans2, meas, backgroundIntensity, calibFileName, directoryPath, filenameBase, saveCounter):
        super().__init__()
        self.spec = spec
        self.inteTimeL = inteTime1
        self.inteTimeE = inteTime2
        self.channelMode = channelMode
        self.scanL = scans1
        self.scanE = scans2
        self.meas = meas
        self.serialComm = serialComm
        self.backgroundIntensity = backgroundIntensity
        self.calibFileName = calibFileName
        self.directoryPath = directoryPath
        self.filenameBase = filenameBase
        self.save_counter = saveCounter
        
    def read_calib_coeff_file(self, filename):
        calibCoeffFile = open(filename, 'r')
        lines = calibCoeffFile.read().splitlines()
        lines = lines[1::] # skip the first line
        Coeff_a = []
        Coeff_b = []
        for line in lines:
            sline = line.split(',')
            Coeff_a.append(float(sline[1]))
            Coeff_b.append(float(sline[2]))
        calibCoeffFile.close()
        return Coeff_a, Coeff_b
    def calc_calib_coeff(self, x, a, b, inte_time):
        integrationTimeArray = np.ones(np.shape(x)) * inte_time
        coeff = np.multiply(a, np.power(integrationTimeArray, b))
        return coeff
    def run(self):
        if self.channelMode == 1 or self.channelMode == 2:
            if self.channelMode == 1:
                inteTime = self.inteTimeL
                scanNum = self.scanL
                self.changeLineEdit2.emit("L: Int. Time (" + str(inteTime/1000) + ") Ave Scans ("+str(scanNum)+")")
            else:
                inteTime = self.inteTimeE
                scanNum = self.scanE
                self.changeLineEdit2.emit("E: Int. Time (" + str(inteTime/1000) + ") Ave Scans ("+str(scanNum)+")")
            
            self.spec.integration_time_micros(inteTime)
            
            QtWidgets.QApplication.processEvents()
            cnt = 0
            x = self.spec.wavelengths()
            a, b = self.read_calib_coeff_file(self.calibFileName)
            calibCoeff = self.calc_calib_coeff(x, a, b, inteTime/1000)
            np.save('coeff',calibCoeff)
            print("current int time: " + str(inteTime))
            spectrum_all = np.zeros((self.meas, len(x)))
            spectrum_calib_all = np.zeros((self.meas, len(x)))
            time_buffer = []
            self.startSaving.emit("Saving in progress")
            for m in range(0, self.meas):
                spectrum_final = [0] * len(x)
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                time_buffer.append(curr_time)
                for s in range(0, scanNum):
                    inten_temp,dark_temp  = self.spec.intensities(correct_dark_counts=True, correct_nonlinearity=False)
                    inten_temp = inten_temp - self.backgroundIntensity
                    spectrum_final = spectrum_final + inten_temp
                    cnt = cnt + 1
                    print("Measuring saving: " + str(int(cnt/(self.meas * scanNum) * 100)))
                    self.setCurrentProgress.emit(int(cnt/(self.meas * scanNum) * 100))
                # print(spectrum_final)
                # print(scanNum)
                spectrum_final = spectrum_final/scanNum
                spectrum_all[m,:] = np.subtract(spectrum_final, self.backgroundIntensity)
                spectrum_calib_all[m,:] = np.multiply(spectrum_all[m,:], calibCoeff)
                np.save('calibData',spectrum_calib_all)
                np.save('rawData',spectrum_all)
                self.finishOneMeasurement.emit()
                
                
            if self.channelMode == 1:
                control_info = "Integration time (L): " + str(self.inteTimeL) + ", Scans to average (L): " + str(self.scanL) +  '\n'
            else:
                control_info = "Integration time (E): " + str(self.inteTimeE) + ", Scans to average (E): " + str(self.scanE) +  '\n'
            filename = self.directoryPath + '\\'+self.filenameBase + '_'+self.spec.model+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'_' +str(self.save_counter)+'.txt'
            outfile = open(filename,'w')
            headerInfo = "Wavelength (nm)" + ","
            # + "Intensity 1 (L)," + "Intensity 1 calibrated (L)," + "Intensity 1 (E)," + "Intensity 1 calibrated (E)," + "Intensity 2 (L)," + "Intensity 2 calibrated (L)," + "Intensity 2 (E)," + "Intensity 2 calibrated (E),"+ "Intensity 3 (L)," + "Intensity 3 calibrated (L),"+ "Intensity 3 (E)," + "Intensity 3 calibrated (E),"+ "Intensity 4 (L)," + "Intensity 4 calibrated (L),"+ "Intensity 4 (E)," + "Intensity 4 calibrated (E),"+ "Intensity 5 (L)," + "Intensity 5 calibrated (L),"+ "Intensity 5 (E)," + "Intensity 5 calibrated (E),"+ "Reflectance," + "Background\n"
            for j in range(0, self.meas):
                if self.channelMode == 1:
                    headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (L)," + "Intensity "+str(j+1)+" calibrated (L)," 
                else:
                    headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (E)," + "Intensity "+str(j+1)+" calibrated (E)," 
            # for i in range(0, self.meas):
            #     headerInfo = headerInfo + "Time ("+str(i+1) +")," +"Intensity "+str(i+1)+" (E)," + "Intensity "+str(i+1)+" calibrated (E)," + "Reflectance " + str(i+1)+","
            headerInfo = headerInfo + "Background, " + control_info + "\n"
            outfile.write(headerInfo)
            
            for n in range(0, len(x)):
                lineInput = str(x[n]) + ','
                for j in range(0, self.meas):
                    # intensity_calib = spectrum_all[j,n] * calibCoeff[n]
                    lineInput = lineInput + time_buffer[j] + ','+ str(spectrum_all[j,n]) + ',' + str(spectrum_calib_all[j,n]) + ','
                    # lineInput = lineInput + intensityL_temp_time_buffer[i] + ',' + str(round(intensityL_temp_buffer[n,i])) + ',' + str(round(intensityL_calib)) + ','  + str(round(reflectance)) + ','
                lineInput = lineInput + str(self.backgroundIntensity[n]) + '\n'
                outfile.write(lineInput)
        #     # 
            outfile.close()
            # self.save_counter = self.save_counter + 1
            if (self.channelMode == 1):
                specDataL = np.ndarray.tolist(spectrum_final)
                specDataE = []
            else:
                specDataE = np.ndarray.tolist(spectrum_final)
                specDataL = []
            self.succeeded2.emit(specDataL, specDataE)
            time.sleep(1)
            winsound.Beep(1000,300)
        else:
            cnt = 0
            QtWidgets.QApplication.processEvents()
            x = self.spec.wavelengths()
            a, b = self.read_calib_coeff_file(self.calibFileName)
            calibCoeff = self.calc_calib_coeff(x, a, b, inteTime)
            spectrum_all_E = np.zeros((self.meas, len(x)))
            spectrum_all_L = spectrum_all_E
            spectrum_all_E_calib = spectrum_all_E
            spectrum_all_L_calib = spectrum_all_L
            time_buffer_E = []
            time_buffer_L = []
            for m in range(0, self.meas):
                self.changeLineEdit2.emit("L: Int. Time (" + str(self.inteTimeL/1000) + ") Ave Scans ("+str(self.scanL)+")")
                self.serialComm.write('on'.encode())
                time.sleep(1)
                self.spec.integration_time_micros(self.inteTimeL)
                spectrum_final = [0] * len(x)
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                time_buffer_L.append(curr_time)
                for s in range(0, self.scanL):
                    inten_temp,dark_temp  = self.spec.intensities(correct_dark_counts=True, correct_nonlinearity=False)
                    spectrum_final = spectrum_final + inten_temp
                    cnt = cnt + 1
                    print("Measuring saving: " + str(int(cnt/(self.meas * (self.scanL + self.scanE) ) * 100)))
                    self.setCurrentProgress.emit(int(cnt/(self.meas * (self.scanL + self.scanE)) * 100))
                spectrum_all_L[m,:] = np.subtract(spectrum_final/self.scanL, self.backgroundIntensity)
                spectrum_all_L_calib[m,:] = np.multiply(spectrum_all_L[m,:], calibCoeff)
                self.changeLineEdit2.emit("E: Int. Time (" + str(self.inteTimeE/1000) + ") Ave Scans ("+str(self.scanE)+")")
                self.serialComm.write('off'.encode())
                time.sleep(1)
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                time_buffer_E.append(curr_time)
                self.spec.integration_time_micros(self.inteTimeE)
                spectrum_final = [0] * len(x)
                for s in range(0, self.scanE):
                    inten_temp,dark_temp  = self.spec.intensities(correct_dark_counts=True, correct_nonlinearity=False)
                    spectrum_final = spectrum_final + inten_temp
                    cnt = cnt + 1
                    print("Measuring saving: " + str(int(cnt/(self.meas * (self.scanE + self.scanL) ) * 100)))
                    self.setCurrentProgress.emit(int(cnt/(self.meas * (self.scanE + self.scanL)) * 100))  
                spectrum_all_E[m, :] = np.subtrac(spectrum_final/self.scanE, self.backgroundIntensity)
                spectrum_all_E_calib[m,:] = np.multiply(spectrum_all_E[m, :] , calibCoeff)
            control_info = "Integration time (L): " + str(self.inteTimeL) + ", Integration time (E): " + str(self.inteTimeE) + ", Scans to average (L): " + str(self.scanL) + ", Scans to average (E): " + str(self.scanE) + '\n'
            filename = self.directoryPath + '\\'+self.filenameBase + '_'+self.spec.model+'_'+str(self.save_counter)+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'.txt'
            outfile = open(filename,'w')
            headerInfo = "Wavelength (nm)" + ","
            # + "Intensity 1 (L)," + "Intensity 1 calibrated (L)," + "Intensity 1 (E)," + "Intensity 1 calibrated (E)," + "Intensity 2 (L)," + "Intensity 2 calibrated (L)," + "Intensity 2 (E)," + "Intensity 2 calibrated (E),"+ "Intensity 3 (L)," + "Intensity 3 calibrated (L),"+ "Intensity 3 (E)," + "Intensity 3 calibrated (E),"+ "Intensity 4 (L)," + "Intensity 4 calibrated (L),"+ "Intensity 4 (E)," + "Intensity 4 calibrated (E),"+ "Intensity 5 (L)," + "Intensity 5 calibrated (L),"+ "Intensity 5 (E)," + "Intensity 5 calibrated (E),"+ "Reflectance," + "Background\n"
            for j in range(0, self.meas):
                headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (L)," + "Intensity "+str(j+1)+" calibrated (L)," 
            for i in range(0, self.meas):
                headerInfo = headerInfo + "Time ("+str(i+1) +")," +"Intensity "+str(i+1)+" (E)," + "Intensity "+str(i+1)+" calibrated (E)," + "Reflectance " + str(i+1)+","
            headerInfo = headerInfo + "Background, " + control_info + "\n"
            outfile.write(headerInfo)
            for n in range(0, len(x)):
                lineInput = str(x[n]) + ','
                for j in range(0, self.meas):
                    # intensityL_calib = spectrum_all_L[j,n] * self.calibCoeffL[n]
                    lineInput = lineInput + time_buffer_L[j] + ','+ str(spectrum_all_L[j,n]) + ',' + str(spectrum_all_L_calib[j,n]) + ','
                for i in range(0, self.meas):
                    # intensityL_calib = self.intensity_L_queue[i][n] * self.calibCoeff_L[n]
                    # intensityE_calib = spectrum_all_E[i,n] * self.calibCoeffE[n]
                    reference_percentage = 100
                    if (self.meas == 1):
                        reflectance = spectrum_all_E_calib[i,n]/((spectrum_all_E[0,n] * calibCoeff[n])/(reference_percentage/100))
                    else:
                        reflectance = spectrum_all_E_calib[i,n]/((spectrum_all_E[round(self.meas/2),n] * calibCoeff[n])/(reference_percentage/100))
        #             # lineInput = lineInput + str(round(self.intensity_L_queue[i][n])) + ',' + str(round(intensityL_calib)) + ',' + str(round(self.intensity_E_queue[i][n])) + ',' + str(round(intensityE_calib)) + ',' + str(round(reflectance)) + ','
                    lineInput = lineInput + time_buffer_E[i] + ',' + str(spectrum_all_E[i,n]) + ',' + str(spectrum_all_E_calib[i,n]) + ','  + str(reflectance) + ','
                lineInput = lineInput + str(self.backgroundIntensity[n]) + '\n'
                outfile.write(lineInput)
        #     # 
            outfile.close()
            specDataL = np.ndarray.tolist(spectrum_all_L[round(self.meas/2),:])
            specDataE = np.ndarray.tolist(spectrum_all_E[round(self.meas/2),:])
            self.succeeded2.emit(specDataL, specDataE)
            time.sleep(1)
            winsound.Beep(1000,300)
            
        self.succeeded.emit()
    
    # def stop(self):
    #     self.is_running = False
    #     print('Stopping thread ...', self.index)
    #     self.terminate()

class SaveThread(QtCore.QThread):
    startSaving = QtCore.pyqtSignal(str)
    setTotalProgress = QtCore.pyqtSignal(int)
    setCurrentProgress = QtCore.pyqtSignal(int)
    succeeded = QtCore.pyqtSignal()
    succeeded2 = QtCore.pyqtSignal(list, list)
    changeLineEdit2 = QtCore.pyqtSignal(str)
    # dataEReady = QtCore.pyqtSignal(list)
    # dataLReady = QtCore.pyqtSignal(list)
    finishOneMeasurement = QtCore.pyqtSignal()
    def __init__(self, spec, channelMode, serialComm, inteTime1,inteTime2, scans1,scans2, meas, backgroundIntensity, calibCoeff1, calibCoeff2, directoryPath, filenameBase, saveCounter):
        super().__init__()
        self.spec = spec
        self.inteTimeL = inteTime1
        self.inteTimeE = inteTime2
        self.channelMode = channelMode
        self.scanL = scans1
        self.scanE = scans2
        self.meas = meas
        self.serialComm = serialComm
        self.backgroundIntensity = backgroundIntensity
        self.calibCoeffL = calibCoeff1
        self.calibCoeffE = calibCoeff2
        self.directoryPath = directoryPath
        self.filenameBase = filenameBase
        self.save_counter = saveCounter
        
    
    def run(self):
        if self.channelMode == 1 or self.channelMode == 2:
            if self.channelMode == 1:
                inteTime = self.inteTimeL
                scanNum = self.scanL
                calibCoeff = self.calibCoeffL
                self.changeLineEdit2.emit("L: Int. Time (" + str(inteTime/1000) + ") Ave Scans ("+str(scanNum)+")")
            else:
                inteTime = self.inteTimeE
                scanNum = self.scanE
                calibCoeff = self.calibCoeffE
                self.changeLineEdit2.emit("E: Int. Time (" + str(inteTime/1000) + ") Ave Scans ("+str(scanNum)+")")
            
            self.spec.integration_time_micros(inteTime)
            
            QtWidgets.QApplication.processEvents()
            cnt = 0
            x = self.spec.wavelengths()
            print("current int time: " + str(inteTime))
            spectrum_all = np.zeros((self.meas, len(x)))
            time_buffer = []
            self.startSaving.emit("Saving in progress")
            for m in range(0, self.meas):
                spectrum_final = [0] * len(x)
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                time_buffer.append(curr_time)
                for s in range(0, scanNum):
                    inten_temp,dark_temp  = self.spec.intensities(correct_dark_counts=True, correct_nonlinearity=False)
                    inten_temp = inten_temp - self.backgroundIntensity
                    spectrum_final = spectrum_final + inten_temp
                    cnt = cnt + 1
                    print("Measuring saving: " + str(int(cnt/(self.meas * scanNum) * 100)))
                    self.setCurrentProgress.emit(int(cnt/(self.meas * scanNum) * 100))
                # print(spectrum_final)
                # print(scanNum)
                spectrum_final = spectrum_final/scanNum
                spectrum_all[m,:] = np.subtract(spectrum_final, self.backgroundIntensity)
                self.finishOneMeasurement.emit()
                
                
            if self.channelMode == 1:
                control_info = "Integration time (L): " + str(self.inteTimeL) + ", Scans to average (L): " + str(self.scanL) +  '\n'
            else:
                control_info = "Integration time (E): " + str(self.inteTimeE) + ", Scans to average (E): " + str(self.scanE) +  '\n'
            filename = self.directoryPath + '\\'+self.filenameBase + '_'+self.spec.model+'_'+str(self.save_counter)+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'.txt'
            outfile = open(filename,'w')
            headerInfo = "Wavelength (nm)" + ","
            # + "Intensity 1 (L)," + "Intensity 1 calibrated (L)," + "Intensity 1 (E)," + "Intensity 1 calibrated (E)," + "Intensity 2 (L)," + "Intensity 2 calibrated (L)," + "Intensity 2 (E)," + "Intensity 2 calibrated (E),"+ "Intensity 3 (L)," + "Intensity 3 calibrated (L),"+ "Intensity 3 (E)," + "Intensity 3 calibrated (E),"+ "Intensity 4 (L)," + "Intensity 4 calibrated (L),"+ "Intensity 4 (E)," + "Intensity 4 calibrated (E),"+ "Intensity 5 (L)," + "Intensity 5 calibrated (L),"+ "Intensity 5 (E)," + "Intensity 5 calibrated (E),"+ "Reflectance," + "Background\n"
            for j in range(0, self.meas):
                if self.channelMode == 1:
                    headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (L)," + "Intensity "+str(j+1)+" calibrated (L)," 
                else:
                    headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (E)," + "Intensity "+str(j+1)+" calibrated (E)," 
            # for i in range(0, self.meas):
            #     headerInfo = headerInfo + "Time ("+str(i+1) +")," +"Intensity "+str(i+1)+" (E)," + "Intensity "+str(i+1)+" calibrated (E)," + "Reflectance " + str(i+1)+","
            headerInfo = headerInfo + "Background, " + control_info + "\n"
            outfile.write(headerInfo)
            
            for n in range(0, len(x)):
                lineInput = str(x[n]) + ','
                for j in range(0, self.meas):
                    intensity_calib = spectrum_all[j,n] * calibCoeff[n]
                    lineInput = lineInput + time_buffer[j] + ','+ str(round(spectrum_all[j,n])) + ',' + str(round(intensity_calib)) + ','
                    # lineInput = lineInput + intensityL_temp_time_buffer[i] + ',' + str(round(intensityL_temp_buffer[n,i])) + ',' + str(round(intensityL_calib)) + ','  + str(round(reflectance)) + ','
                lineInput = lineInput + str(round(self.backgroundIntensity[n])) + '\n'
                outfile.write(lineInput)
        #     # 
            outfile.close()
            # self.save_counter = self.save_counter + 1
            if (self.channelMode == 1):
                specDataL = np.ndarray.tolist(spectrum_final)
                specDataE = []
            else:
                specDataE = np.ndarray.tolist(spectrum_final)
                specDataL = []
            self.succeeded2.emit(specDataL, specDataE)
            time.sleep(1)
            winsound.Beep(1000,300)
        else:
            cnt = 0
            QtWidgets.QApplication.processEvents()
            x = self.spec.wavelengths()
            spectrum_all_E = np.zeros((self.meas, len(x)))
            spectrum_all_L = spectrum_all_E
            time_buffer_E = []
            time_buffer_L = []
            for m in range(0, self.meas):
                self.changeLineEdit2.emit("L: Int. Time (" + str(self.inteTimeL/1000) + ") Ave Scans ("+str(self.scanL)+")")
                self.serialComm.write('on'.encode())
                time.sleep(1)
                self.spec.integration_time_micros(self.inteTimeL)
                spectrum_final = [0] * len(x)
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                time_buffer_L.append(curr_time)
                for s in range(0, self.scanL):
                    inten_temp,dark_temp  = self.spec.intensities(correct_dark_counts=True, correct_nonlinearity=False)
                    spectrum_final = spectrum_final + inten_temp
                    cnt = cnt + 1
                    print("Measuring saving: " + str(int(cnt/(self.meas * (self.scanL + self.scanE) ) * 100)))
                    self.setCurrentProgress.emit(int(cnt/(self.meas * (self.scanL + self.scanE)) * 100))
                spectrum_all_L[m,:] = np.subtract(spectrum_final/self.scanL, self.backgroundIntensity)
                self.changeLineEdit2.emit("E: Int. Time (" + str(self.inteTimeE/1000) + ") Ave Scans ("+str(self.scanE)+")")
                self.serialComm.write('off'.encode())
                time.sleep(1)
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                time_buffer_E.append(curr_time)
                self.spec.integration_time_micros(self.inteTimeE)
                spectrum_final = [0] * len(x)
                for s in range(0, self.scanE):
                    inten_temp,dark_temp  = self.spec.intensities(correct_dark_counts=True, correct_nonlinearity=False)
                    spectrum_final = spectrum_final + inten_temp
                    cnt = cnt + 1
                    print("Measuring saving: " + str(int(cnt/(self.meas * (self.scanE + self.scanL) ) * 100)))
                    self.setCurrentProgress.emit(int(cnt/(self.meas * (self.scanE + self.scanL)) * 100))  
                spectrum_all_E[m, :] = spectrum_final/self.scanE
            control_info = "Integration time (L): " + str(self.inteTimeL) + ", Integration time (E): " + str(self.inteTimeE) + ", Scans to average (L): " + str(self.scanL) + ", Scans to average (E): " + str(self.scanE) + '\n'
            filename = self.directoryPath + '\\'+self.filenameBase + '_'+self.spec.model+'_'+str(self.save_counter)+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'.txt'
            outfile = open(filename,'w')
            headerInfo = "Wavelength (nm)" + ","
            # + "Intensity 1 (L)," + "Intensity 1 calibrated (L)," + "Intensity 1 (E)," + "Intensity 1 calibrated (E)," + "Intensity 2 (L)," + "Intensity 2 calibrated (L)," + "Intensity 2 (E)," + "Intensity 2 calibrated (E),"+ "Intensity 3 (L)," + "Intensity 3 calibrated (L),"+ "Intensity 3 (E)," + "Intensity 3 calibrated (E),"+ "Intensity 4 (L)," + "Intensity 4 calibrated (L),"+ "Intensity 4 (E)," + "Intensity 4 calibrated (E),"+ "Intensity 5 (L)," + "Intensity 5 calibrated (L),"+ "Intensity 5 (E)," + "Intensity 5 calibrated (E),"+ "Reflectance," + "Background\n"
            for j in range(0, self.meas):
                headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (L)," + "Intensity "+str(j+1)+" calibrated (L)," 
            for i in range(0, self.meas):
                headerInfo = headerInfo + "Time ("+str(i+1) +")," +"Intensity "+str(i+1)+" (E)," + "Intensity "+str(i+1)+" calibrated (E)," + "Reflectance " + str(i+1)+","
            headerInfo = headerInfo + "Background, " + control_info + "\n"
            outfile.write(headerInfo)
            for n in range(0, len(x)):
                lineInput = str(x[n]) + ','
                for j in range(0, self.meas):
                    intensityL_calib = spectrum_all_L[j,n] * self.calibCoeffL[n]
                    lineInput = lineInput + time_buffer_L[j] + ','+ str(round(spectrum_all_L[j,n])) + ',' + str(round(intensityL_calib)) + ','
                for i in range(0, self.meas):
                    # intensityL_calib = self.intensity_L_queue[i][n] * self.calibCoeff_L[n]
                    intensityE_calib = spectrum_all_E[i,n] * self.calibCoeffE[n]
                    reference_percentage = 100
                    if (self.meas == 1):
                        reflectance = intensityL_calib/((spectrum_all_E[0,n] * self.calibCoeffE[n])/(reference_percentage/100))
                    else:
                        reflectance = intensityL_calib/((spectrum_all_E[round(self.meas/2),n] * self.calibCoeffE[n])/(reference_percentage/100))
        #             # lineInput = lineInput + str(round(self.intensity_L_queue[i][n])) + ',' + str(round(intensityL_calib)) + ',' + str(round(self.intensity_E_queue[i][n])) + ',' + str(round(intensityE_calib)) + ',' + str(round(reflectance)) + ','
                    lineInput = lineInput + time_buffer_E[i] + ',' + str(round(spectrum_all_E[i,n])) + ',' + str(round(intensityE_calib)) + ','  + str(round(reflectance)) + ','
                lineInput = lineInput + str(round(self.backgroundIntensity[n])) + '\n'
                outfile.write(lineInput)
        #     # 
            outfile.close()
            specDataL = np.ndarray.tolist(spectrum_all_L[round(self.meas/2),:])
            specDataE = np.ndarray.tolist(spectrum_all_E[round(self.meas/2),:])
            self.succeeded2.emit(specDataL, specDataE)
            time.sleep(1)
            winsound.Beep(1000,300)
            
        self.succeeded.emit()
    
    # def stop(self):
    #     self.is_running = False
    #     print('Stopping thread ...', self.index)
    #     self.terminate()

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)

class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''
    def __init__(self, function, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.function(
                *self.args, **self.kwargs
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=7, height=2, dpi=300):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.set_facecolor((0,0,0))
        # fig, self.axes = plt.subplots(3,3)
        self.axes = fig.add_subplot(111)
        # self.axes = fig.add_subplot(222)
        super(MplCanvas, self).__init__(fig)
        fig.tight_layout()
class MainWindow(QtWidgets.QMainWindow):
    doneSignal = pyqtSignal()
    busySignal = pyqtSignal()
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('main12.ui',self)
        # self.title = 'HyperSens Spectrometer Software'
        self.ui.setWindowTitle('HyperSens Spectrometer Software')
        # Find the connected spectrometer
        self.device_list = []
        self.ui.comboBox_2.addItems(self.device_list)
        self.ui.comboBox_2.setCurrentIndex(0)
        
        # Find if the FoS switch is connected
        self.ui.comboBox.addItems(['Both','L (Radiance)','E (Irradiance)'])
        if port is None:
            self.isArduino = False
            self.serialcomm = None
            self.ui.comboBox.setCurrentIndex(1) # if arduino (FoS) is not connected, L mode is the default mode
        else:
            self.isArduino = True
            self.serialcomm = serial.Serial(port, 9600)
            self.serialcomm.timeout = 1 
            self.ui.comboBox.setCurrentIndex(0)

        # self.ui.comboBox.setEnabled(False)
        self.directoryPath = os.getcwd()
        self.ui.lineEdit.setText(self.directoryPath)
        self.ui.pushButton_21.clicked.connect(self.newDirectory)

        self.SpectrometerIndicator = QLed(onColour=QLed.Green, offColour=QLed.Red, shape=QLed.Circle)
        self.ui.horizontalLayout_10.addWidget(self.SpectrometerIndicator)
        # self.ui.pushButton_9.setEnabled(False)
        # self.ui.pushButton_12.setEnabled(False)
        # self.ui.spinBox.setEnabled(False)
        self.ui.pushButton_12.setEnabled(False)
        self.ui.pushButton_9.setEnabled(False)
        self.ui.pushButton_14.setEnabled(False)
        self.ui.pushButton_13.setEnabled(False)
        self.ui.pushButton_6.setEnabled(False)
        self.ui.pushButton_5.setEnabled(False)
        self.ui.pushButton_17.setEnabled(False)
        self.ui.pushButton_18.setEnabled(False)
        self.ui.pushButton_19.setEnabled(False)
        # self.ui.pushButton_22.setEnabled(False)
        self.ui.pushButton_20.setEnabled(False)
        # self.ui.pushButton_20.setEnabled(False)
        # self.ui.pushButton_22.setEnabled(False)
        self.ui.pushButton_23.setEnabled(False)

        self.ui.comboBox.currentIndexChanged.connect(self.setFibreMode)
        # self.ui.checkBox.setCheckable(True)
        # self.ui.checkBox.clicked.connect(self.EOnlyFibreMode)
        # self.ui.checkBox_3.setCheckable(True)
        # self.ui.checkBox_3.clicked.connect(self.LOnlyFibreMode)
        # self.ui.checkBox_4.setCheckable(True)
        # self.ui.checkBox_4.setChecked(True)
        # # self.BothFibreMode()
        # self.ui.checkBox_4.clicked.connect(self.BothFibreMode)
        self.ui.pushButton_11.clicked.connect(self.initializeSpectrometer)
        # self.if_L = True
        self.ui.checkBox_2.setCheckable(True)
        self.ui.checkBox_2.clicked.connect(self.trigger_switched)
        ######### plot range ########
        self.if_range_changed = False
        self.debounce = QTimer()
        self.debounce.setInterval(1000)
        self.debounce.setSingleShot(True)
        self.debounce.timeout.connect(self.textInputDoneLeft)
        self.ui.doubleSpinBox_13.textChanged.connect(self.debounce.start)
        self.debounce2 = QTimer()
        self.debounce2.setInterval(1000)
        self.debounce2.setSingleShot(True)
        self.debounce2.timeout.connect(self.textInputDoneRight)
        self.ui.doubleSpinBox_14.textChanged.connect(self.debounce2.start)
        ######### set integration times #######
        self.ui.pushButton_12.clicked.connect(self.setSpecIntTime)
        self.ui.pushButton_9.clicked.connect(self.setSpecIntTime)
        self.isIntTimeChanged = False
        ######### set scans to avg #######
        self.ui.pushButton_14.clicked.connect(self.setScansToAvg)
        self.ui.pushButton_13.clicked.connect(self.setScansToAvg)
        ######### number of measurememnts saved #######
        # self.ui.pushButton_22.clicked.connect(self.setMeasNumE)
        self.ui.pushButton_23.clicked.connect(self.setMeasNum2)
        ######### Quit program ########
        self.ui.pushButton.clicked.connect(self.close_application) # quit button
        ######### optimize integration time #########
        self.ui.pushButton_5.clicked.connect(self.startOptimize)
        # self.ui.pushButton_17.clicked.connect(self.startOptimize)
        ######### measure background #########
        self.ui.pushButton_6.clicked.connect(self.measureBackground)
        # self.ui.pushButton_15.clicked.connect(self.measureBackground)
        ######### spectra measurement #########
        # self.ui.pushButton_8.clicked.connect(self.startWorker)
        self.ui.pushButton_18.clicked.connect(self.startWorker)
        self.ui.pushButton_20.clicked.connect(self.stopWorker)
        # self.ui.pushButton_22.clicked.connect(self.refreshGUI)
        # self.ui.pushButton_19.clicked.connect(self.stopWorker)
        self.ui.pushButton_19.clicked.connect(self.saveSpectraMultiple)
        ######### get calibration file #########
        self.ui.pushButton_2.clicked.connect(self.open_calib_coeff_file_L) # get calibration coeff file for L
        self.ui.pushButton_3.clicked.connect(self.open_calib_coeff_file_E) # get calibration coeff file for E
        # self.ui.pushButton_4.setCheckable(True)
        # self.ui.pushButton_7.setCheckable(True)
        self.applyCalibE = False
        self.applyCalibL = False
        # self.ui.pushButton_4.clicked.connect(self.applyCalibration)
        # self.ui.pushButton_7.clicked.connect(self.applyCalibration)
        ######### Save ########
        # self.ui.pushButton_10.setCheckable(True)
        # self.ui.pushButton_10.clicked.connect(self.saveSpectra)
        self.ui.pushButton_17.clicked.connect(self.saveSpectraOne)
        self.ui.progressBar.setMaximum(100)
        self.ui.progressBar.setValue(0)
        # self.ui.pushButton_20.clicked.connect(self.saveSpectra4)
        ######### Plots ########
        titles = ['Raw L', 'Raw E', 'Dark', 'Calibrated L (full)', 'Calibrated E (full)', 'Reflectance (full)', 'Calibrated L (A-B)','Calibrated E (A-B)', 'Reflectance (A-B)']
        self.canvases = []
        self.reference_plots = []
        self.plot_datas = []
        for i in range(0,3):
            for j in range(0,3):
                newCanvas = MplCanvas(self, width=4, height=2, dpi=100)
                newCanvas.axes.set_facecolor((0,0,0))
                newCanvas.axes.tick_params(axis = 'x',color='w')
                newCanvas.axes.tick_params(axis = 'y',color='w')
                newCanvas.axes.xaxis.label.set_color('w')
                newCanvas.axes.yaxis.label.set_color('w') 
                newCanvas.axes.spines['left'].set_color('w')
                newCanvas.axes.spines['bottom'].set_color('w') 
                newCanvas.axes.set_title(titles[i * 3 + j])
                newCanvas.axes.set_xlabel("Wavelength (nm)",fontsize=8)
                newCanvas.axes.set_ylabel("Intensity",fontsize=8)
                [t.set_color('w') for t in newCanvas.axes.xaxis.get_ticklabels()]
                [t.set_color('w') for t in newCanvas.axes.yaxis.get_ticklabels()]
                self.canvases.append(newCanvas)
        # self.canvas.axes[0,1].set_facecolor((0,0,0))
        # self.canvas.axes[0,2].set_facecolor((0,0,0))
        # self.canvas.axes[1,1].set_facecolor((0,0,0))
                self.reference_plots.append(None)
                self.plot_datas.append(None)
                if i == 0:
                    self.ui.verticalLayout_20.addWidget(newCanvas)
                elif i == 1:
                    self.ui.verticalLayout.addWidget(newCanvas)
                else:
                    self.ui.verticalLayout_4.addWidget(newCanvas)

        # self.canvas2 = MplCanvas(self, width=6, height=2, dpi=100)
        # self.canvas2.axes.set_facecolor((0,0,0))
        # self.canvas2.axes.set_title("Raw E")
        # self.canvas2.axes.set_xlabel("Wavelength (nm)")
        # self.canvas2.axes.set_ylabel("Intensity")
        # # self.canvas.axes[0,1].set_facecolor((0,0,0))
        # # self.canvas.axes[0,2].set_facecolor((0,0,0))
        # # self.canvas.axes[1,1].set_facecolor((0,0,0))
        # self.reference_plot2 = None
        # self.ui.verticalLayout_20.addWidget(self.canvas2)

        # self.canvas3 = MplCanvas(self, width=6, height=2, dpi=100)
        # self.canvas3.axes.set_facecolor((0,0,0))
        # self.canvas3.axes.set_title("Dark")
        # self.canvas3.axes.set_xlabel("Wavelength (nm)")
        # self.canvas3.axes.set_ylabel("Intensity")
        # # self.canvas.axes[0,1].set_facecolor((0,0,0))
        # # self.canvas.axes[0,2].set_facecolor((0,0,0))
        # # self.canvas.axes[1,1].set_facecolor((0,0,0))
        # self.reference_plot3 = None
        # self.ui.verticalLayout_20.addWidget(self.canvas3)
        ######### Results ########
        self.ui.pushButton_4.clicked.connect(self.setInRange1)
        self.ui.pushButton_7.clicked.connect(self.setInRange2)
        self.ui.pushButton_8.clicked.connect(self.setOutLeftRange1)
        self.ui.pushButton_10.clicked.connect(self.setOutLeftRange2)
        self.ui.pushButton_15.clicked.connect(self.setOutRightRange1)
        self.ui.pushButton_16.clicked.connect(self.setOutRightRange2)
        ######### Data processing ########
        self.threadpool = QtCore.QThreadPool()	
        self.threadpool.setMaxThreadCount(10)
        self.q = queue.Queue(maxsize = 20)
        self.wavelength = None
        self.intensity = None
        self.dark_mean = 0
        self.intensity_E = None
        self.intensity_E_ref = None 
        self.intensity_L_ref = None
        self.intensity_L = None 
        self.backgroundIntensity = None  
        self.calib_file_name_E = None 
        self.calib_file_name_L = None 
        self.intensity_buffersize = 1
        # self.intensity_L_buffersize = 1
        self.updateRate = 100 # millisecond
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.updateRate)
        
        self.timer.timeout.connect(self.plotSpectra)
        self.timer.start()
        self.worker = None 
        self.isStopped = True
        self.isTerminated = True
        self.show()
    def updateResults(self):
        self.Ein_687 = self.getResultsMin(self.plot_datas[3], self.InRange1Min, self.InRange1Max)
        self.Lin_687 = self.getResultsMin(self.plot_datas[4], self.InRange1Min, self.InRange1Max)
        self.Eout_left_687 = self.getResultsMax(self.plot_datas[3], self.OutLeftRange1Min, self.OutLeftRange1Max)
        self.Eout_right_687 = self.getResultsMax(self.plot_datas[3], self.OutRightRange1Min, self.OutRightRange1Max)
        self.Lout_left_687 = self.getResultsMax(self.plot_datas[4], self.OutLeftRange1Min, self.OutLeftRange1Max)
        self.Lout_right_687 = self.getResultsMax(self.plot_datas[4], self.OutRightRange1Min, self.OutRightRange1Max)
        wL687 = (self.Eout_right_687[0] - self.Ein_687[0])/(self.Eout_right_687[0] - self.Eout_left_687[0])
        wL760 = (self.Eout_right_760[0] - self.Ein_760[0])/(self.Eout_right_760[0] - self.Eout_left_760[0])
        wR687 = (self.Ein_687[0] - self.Eout_left_687[0])/(self.Eout_right_687[0] - self.Eout_left_687[0])
        wR760 = (self.Ein_760[0] - self.Eout_left_760[0])/(self.Eout_right_760[0] - self.Eout_left_760[0])
        
        FLD1 = (((wL687 * self.Eout_left_687[1] + wR687 * self.Eout_right_687[1]) * self.Lin_687[1])-(self.Ein_687[1]*(wL687 * self.Lout_left_687[1] + wR687 * self.Lout_right_687[1])))/((wL687 * self.Eout_left_687[1] + wR687 * self.Eout_right_687[1])-self.Ein_687[1])
        FLD2 = (((wL760 * self.Eout_left_760[1] + wR760 * self.Eout_right_760[1]) * self.Lin_760[1])-(self.Ein_760[1]*(wL760 * self.Lout_left_760[1] + wR760 * self.Lout_right_760[1])))/((wL760 * self.Eout_left_760[1] + wR760 * self.Eout_right_760[1])-self.Ein_760[1])
                        
        # FLD1 = ((np.mean([self.Eout_left_687[1], self.Eout_right_687[1]]) * self.Lin_687[1])-(self.Ein_687[1]*np.mean([self.Lout_left_687[1], self.Lout_right_687[1]])))/(np.mean([self.Eout_left_687[1], self.Eout_right_687[1]])-self.Ein_687[1])
        # FLD2 = ((np.mean([self.Eout_left_760[1], self.Eout_right_760[1]]) * self.Lin_760[1])-(self.Ein_760[1]*np.mean([self.Lout_left_760[1], self.Lout_right_760[1]])))/(np.mean([self.Eout_left_760[1], self.Eout_right_760[1]])-self.Ein_760[1])
        self.ui.lineEdit_13.setText(str(round(FLD1,3))) 
        self.ui.lineEdit_15.setText(str(round(FLD2,3)))
    def setInRange1(self):
        self.InRange1Min = self.ui.doubleSpinBox_3.value()
        self.InRange1Max = self.ui.doubleSpinBox_4.value()
        if self.isStopped:
            if self.plot_datas[3] is not None and self.plot_datas[4] is not None:
                print("Start calculate")
                QtWidgets.QApplication.processEvents()
                self.updateResults()  
                
    def setInRange2(self):
        self.InRange2Min = self.ui.doubleSpinBox.value()
        self.InRange2Max = self.ui.doubleSpinBox_2.value()
        if self.isStopped:
            if self.plot_datas[3] is not None and self.plot_datas[4] is not None:
                print("Start calculate")
                QtWidgets.QApplication.processEvents()
                self.updateResults()
    def setOutLeftRange1(self):
        self.OutLeftRange1Min = self.ui.doubleSpinBox_5.value()
        self.OutLeftRange1Max = self.ui.doubleSpinBox_6.value()
        if self.isStopped:
            if self.plot_datas[3] is not None and self.plot_datas[4] is not None:
                print("Start calculate")
                QtWidgets.QApplication.processEvents()
                self.updateResults()
    def setOutLeftRange2(self):
        self.OutLeftRange2Min = self.ui.doubleSpinBox_7.value()
        self.OutLeftRange2Max = self.ui.doubleSpinBox_8.value()
        if self.isStopped:
            if self.plot_datas[3] is not None and self.plot_datas[4] is not None:
                print("Start calculate")
                QtWidgets.QApplication.processEvents()
                self.updateResults()
    def setOutRightRange1(self):
        self.OutRightRange1Min = self.ui.doubleSpinBox_9.value()
        self.OutRightRange1Max = self.ui.doubleSpinBox_10.value()
        if self.isStopped:
            if self.plot_datas[3] is not None and self.plot_datas[4] is not None:
                print("Start calculate")
                QtWidgets.QApplication.processEvents()
                self.updateResults()
    def setOutRightRange2(self):
        self.OutRightRange2Min = self.ui.doubleSpinBox_11.value()
        self.OutRightRange2Max = self.ui.doubleSpinBox_12.value()
        if self.isStopped:
            if self.plot_datas[3] is not None and self.plot_datas[4] is not None:
                print("Start calculate")
                QtWidgets.QApplication.processEvents()
                self.updateResults()
    def textInputDoneLeft(self):
        self.plotRangeLeft = self.ui.doubleSpinBox_13.value()
        self.reference_plots[6] = None
        self.reference_plots[7] = None
        self.reference_plots[8] = None
        self.canvases[6].axes.clear()
        self.canvases[7].axes.clear()
        self.canvases[8].axes.clear()
        self.if_range_changed = True
        print("plot range left: " + str(self.plotRangeLeft))
    def textInputDoneRight(self):
        self.plotRangeRight = self.ui.doubleSpinBox_14.value()
        self.reference_plots[6] = None
        self.reference_plots[7] = None
        self.reference_plots[8] = None
        self.canvases[6].axes.clear()
        self.canvases[7].axes.clear()
        self.canvases[8].axes.clear()
        self.if_range_changed = True
        print("plot range right: " + str(self.plotRangeRight))
    
    def getMeasurement(self):
        print("Get measurement")
        try:
            QtWidgets.QApplication.processEvents()
            while True:
                if self.isStopped:
                    break
                if self.isIntTimeChanged:
                    if self.if_L:
                        self.spec.integration_time_micros(self.int_time_L)
                    else:
                        self.spec.integration_time_micros(self.int_time_E)
                    self.isIntTimeChanged = False
                QtWidgets.QApplication.processEvents()
                self.intensity, self.dark_mean = self.getSpectra(correct_dark_counts=self.correct_dark_counts, correct_nonlinearity=self.correct_nonlinearity)
                if self.if_L:
                    # self.intensity_L_queue.pop(0)
                    # self.intensity_L_queue.append([a- b for a,b in zip(self.intensity,self.backgroundIntensity)])
                    # for i in range(0,self.intensity_L_buffersize):
                    #     self.intensity = self.getSpectra()
                    #     self.intensity_L_buffer[:,i] = self.intensity
                    self.intensity_L = [a-b for a,b in zip(self.intensity, self.backgroundIntensity)]
                else:
                    # curr_time = datetime.now().strftime("%H:%M:%S:%f")
                    # self.intensity_E_time_queue.pop(0)
                    # self.intensity_E_time_queue.append(curr_time)
                    # self.intensity_E_queue.pop(0)
                    # self.intensity_E_queue.append([a- b for a,b in zip(self.intensity,self.backgroundIntensity)])
                    # for i in range(0,self.intensity_E_buffersize):
                    #     self.intensity = self.getSpectra()
                    #     self.intensity_E_buffer[:,i] = self.intensity
                    self.intensity_E = [a- b for a,b in zip(self.intensity,self.backgroundIntensity)]
                if max(self.intensity) > self.spec.max_intensity * 0.9:
                    self.ui.pushButton_5.setStyleSheet("QPushButton {background-color: rgb(255,0,0)}")
                    self.ui.lineEdit_2.setText("Saturation detected, integration time optimization recommended.")
                else:
                    self.ui.pushButton_5.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
                    
                input_data = [a - b for a, b in zip(self.intensity, self.backgroundIntensity)] 
                self.q.put(input_data)
                
        except Exception as e:
            print("ERROR: ", e)
    def startMeasurement(self):
        print("Start measurement")
        self.getMeasurement()
    
            
    def startWorker(self):
        # self.if_L = True
        # print("Start Worker")
        self.if_range_changed = False
        self.ui.pushButton_18.setEnabled(False)
        self.ui.pushButton.setEnabled(False)
        self.ui.pushButton_5.setEnabled(False)
        # self.ui.pushButton_17.setEnabled(False)
        # self.ui.pushButton_19.setEnabled(False)
        # need to disable the fibre mode selection
        self.ui.comboBox.setEnabled(False)
        # self.ui.checkBox.setEnabled(False)
        # self.ui.checkBox_3.setEnabled(False)
        # self.ui.checkBox_4.setEnabled(False)
        for i in range(0,9):
            # print("Close canvas")
            self.canvases[i].axes.clear()
        # for i in range(0,3):
        #     for j in range(0,3):
        #         self.canvas.axes[i,j].clear()
        self.isStopped = False
        self.isTerminated = True
        self.doneSignal.connect(self.enableSave)
        self.busySignal.connect(self.disableSave)
        self.worker = Worker(self.startMeasurement,)
        self.threadpool.start(self.worker)
        print('Start')
        for i in range(0,9):
            self.reference_plots[i] = None
            # self.plot_datas[i] = None
        # self.plot_datas[0] = None
        # self.plot_datas[3] = None
        # self.plot_datas[6] = None
        # self.timer.setInterval(int(self.updateRate))
    def refreshGUI(self):
        self.isStopped = True
        self.isTerminated = True
        self.threadpool.clear()
        self.saver.quit()
        self.ui.pushButton_18.setEnabled(True)
        
    def stopWorker(self):
        self.isStopped = True
        time.sleep(max(self.int_time_E, self.int_time_L)/1000000)
        QtWidgets.QApplication.processEvents()
        self.ui.pushButton_18.setEnabled(True)
        self.ui.pushButton.setEnabled(True)
        self.ui.pushButton_5.setEnabled(True)
        self.ui.pushButton_19.setEnabled(True)
        self.ui.pushButton_17.setEnabled(True)
        self.ui.comboBox.setEnabled(True)
        # self.ui.checkBox.setEnabled(True)
        # self.ui.checkBox_3.setEnabled(True)
        # self.ui.checkBox_4.setEnabled(True)
        pg.QtGui.QGuiApplication.processEvents() 
        if self.if_L is False:
            if(self.reference_plots[0] is not None and self.reference_plots[3] is not None and self.reference_plots[6] is not None):
                self.reference_plots[0].set_alpha(0.4)
                self.reference_plots[3].set_alpha(0.4)
                self.reference_plots[6].set_alpha(0.4)
                self.canvases[0].draw()
                self.canvases[3].draw()
                self.canvases[6].draw()
        else:
            if(self.reference_plots[1] is not None and self.reference_plots[4] is not None and self.reference_plots[7] is not None):
                self.reference_plots[1].set_alpha(0.4)
                self.reference_plots[4].set_alpha(0.4)
                self.reference_plots[7].set_alpha(0.4)
                self.canvases[1].draw()
                self.canvases[4].draw()
                self.canvases[7].draw()
        # self.intensity = None
        with self.q.mutex:
            self.q.queue.clear()
    def close_application(self):
        self.ui.lineEdit_2.setText("Program is closing")
        self.serialcomm.close()
        time.sleep(1) #This pauses the program for 3 seconds
        self.threadpool.thread().quit()
        sys.exit()
    def read_calib_coeff_file(self, filename):
        calibCoeffFile = open(filename, 'r')
        lines = calibCoeffFile.read().splitlines()
        lines = lines[1::] # skip the first line
        Coeff_a = []
        Coeff_b = []
        for line in lines:
            sline = line.split(',')
            Coeff_a.append(float(sline[1]))
            Coeff_b.append(float(sline[2]))
        calibCoeffFile.close()
        return Coeff_a, Coeff_b
    def calc_calib_coeff(self, x, a, b, inte_time):
        inte_time = inte_time/1000
        integrationTimeArray = np.ones(np.shape(x)) * inte_time
        coeff = np.multiply(a, np.power(integrationTimeArray, b))
        return coeff

    def read_calib_file(self, filename):
        self.ui.lineEdit_2.setText("Open " + filename)
        calibFile = open(filename,'r')
        lines = calibFile.read().splitlines()
        lines = lines[1::] # skip the first line
        calibCoeff = []
        for line in lines:
            sline = line.split(',')
            calibCoeff.append(float(sline[1]))
        calibFile.close()
        return calibCoeff
    def open_calib_coeff_file_L(self):
        self.calib_coeff_file_name_L = QtWidgets.QFileDialog.getOpenFileName(None, "Open", "", "")
        if (self.calib_coeff_file_name_L[0] != ''):
            a, b = self.read_calib_coeff_file(self.calib_coeff_file_name_L[0])
            self.calibCoeff_L = self.calc_calib_coeff(self.wavelength, a, b, self.int_time_L)
            self.a_L = a
            self.b_L = b
    def open_calib_coeff_file_E(self):
        self.calib_coeff_file_name_E = QtWidgets.QFileDialog.getOpenFileName(None, "Open", "", "")
        if (self.calib_coeff_file_name_E[0] != ''):
            a, b = self.read_calib_coeff_file(self.calib_coeff_file_name_E[0])
            self.calibCoeff_E = self.calc_calib_coeff(self.wavelength, a, b, self.int_time_E)
            self.a_E = a
            self.b_E = b 
    def open_calib_file_L(self):
        self.calibCoeff_L = []
        self.calib_file_name_L = QtWidgets.QFileDialog.getOpenFileName(None, "Open","","")
        if (self.calib_file_name_L[0] != ''):
            self.calibCoeff_L = self.read_calib_file(self.calib_file_name_L[0])
    def open_calib_file_E(self):
        self.calibCoeff_E = []
        self.calib_file_name_E = QtWidgets.QFileDialog.getOpenFileName(None, "Open","","")
        if (self.calib_file_name_E[0] != ''):
            self.calibCoeff_E = self.read_calib_file(self.calib_file_name_E[0])
    def applyCalibration(self):
        if(self.if_L):
            self.applyCalibL = True
        else:
            self.applyCalibE = True
        # calibFile.close()
    # def startSaving(self):
        # worker = Worker(self.saveSpectra)
        # self.threadpool.start(worker)
    def updatePlotAfterSaving(self, specDataL, specDataE):
        if (len(specDataL) >0 ):
            QtWidgets.QApplication.processEvents()
            specDataL = np.subtract(specDataL, self.backgroundIntensity)
            self.canvases[1].axes.set_ylim(ymin = min(specDataL[1::]), ymax= max(specDataL[1::]))
            self.canvases[1].axes.set_xlabel('Wavelength (nm)')
            self.canvases[1].axes.set_ylabel('Intensity ')
            self.canvases[1].axes.set_title("Raw L", color='w')
            [t.set_color('w') for t in self.canvases[1].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[1].axes.yaxis.get_ticklabels()]
            self.plot_datas[1] = specDataL
            if self.reference_plots[1] is None:
                plot_refs = self.canvases[1].axes.plot(self.wavelength[1::],specDataL[1::], color=(0,1,0.29), alpha = 0.4)
                self.reference_plots[1] = plot_refs[0]	
            else:
                self.reference_plots[1].set_ydata(specDataL[1::])
                self.reference_plots[1].set_alpha(0.4)
            self.canvases[1].draw()
            specDataL_calib = np.multiply(specDataL, self.calibCoeff_L)
            self.intensity_L_ref = specDataL_calib
            min_y = min(specDataL_calib[min(self.wminmax):max(self.wminmax)])
            max_y = max(specDataL_calib[min(self.wminmax):max(self.wminmax)])
            self.canvases[4].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[4].axes.set_xlim(xmin = self.wavelength[min(self.wminmax)], xmax = self.wavelength[max(self.wminmax)])
            self.canvases[4].axes.set_xlabel('Wavelength (nm)')
            self.canvases[4].axes.set_ylabel('Intensity ')
            self.canvases[4].axes.set_title("Calib L", color='w')
            [t.set_color('w') for t in self.canvases[4].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[4].axes.yaxis.get_ticklabels()]
            self.plot_datas[4] = specDataL_calib
            if self.reference_plots[4] is None:
                plot_refs = self.canvases[4].axes.plot(self.wavelength[1::],specDataL_calib[1::], color=(0,1,0.29), alpha = 0.4)
                self.reference_plots[4] = plot_refs[0]	
            else:
                self.reference_plots[4].set_ydata(specDataL_calib[1::])
                self.reference_plots[4].set_alpha(0.4)
            self.canvases[4].draw()
            wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
        # print(self.wavelength[min(wAB)])
        # print(self.wavelength[max(wAB)])
            min_y = min(specDataL_calib[min(wAB):max(wAB)])
            max_y = max(specDataL_calib[min(wAB):max(wAB)])
            self.canvases[7].axes.clear()
            self.canvases[7].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[7].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
            self.canvases[7].axes.set_xlabel('Wavelength (nm)')
            self.canvases[7].axes.set_ylabel('Intensity ')
            self.canvases[7].axes.set_title("Calib L (A-B)",color='w')
            [t.set_color('w') for t in self.canvases[7].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[7].axes.yaxis.get_ticklabels()]
            self.plot_datas[7] = specDataL_calib
            plot_refs = self.canvases[7].axes.plot(self.wavelength, specDataL_calib, color=(0,1,0.29), alpha = 0.4)
            self.reference_plots[7] = plot_refs[0]	
            self.canvases[7].draw()
            if self.intensity_E_ref is not None:
                self.updateFLD(self.intensity_L_ref, self.intensity_E_ref)
        if (len(specDataE) > 0):
            QtWidgets.QApplication.processEvents()
            specDataE = np.subtract(specDataE, self.backgroundIntensity)
            self.canvases[0].axes.set_ylim(ymin = min(specDataE[1::]), ymax= max(specDataE[1::]))
            self.canvases[0].axes.set_xlabel('Wavelength (nm)')
            self.canvases[0].axes.set_ylabel('Intensity ')
            self.canvases[0].axes.set_title("Raw E", color='w')
            [t.set_color('w') for t in self.canvases[0].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[0].axes.yaxis.get_ticklabels()]
            self.plot_datas[0] = specDataL
            if self.reference_plots[0] is None:
                plot_refs = self.canvases[0].axes.plot(self.wavelength[1::],specDataE[1::], color=(0,1,0.29), alpha = 0.4)
                self.reference_plots[0] = plot_refs[0]	
            else:
                self.reference_plots[0].set_ydata(specDataE[1::])
                self.reference_plots[0].set_alpha(0.4)
            self.canvases[0].draw()

            specDataE_calib = np.multiply(specDataE, self.calibCoeff_E)
            self.intensity_E_ref = specDataE_calib
            min_y = min(specDataE_calib[min(self.wminmax):max(self.wminmax)])
            max_y = max(specDataE_calib[min(self.wminmax):max(self.wminmax)])
            self.canvases[3].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[3].axes.set_xlim(xmin = self.wavelength[min(self.wminmax)], xmax = self.wavelength[max(self.wminmax)])
            self.canvases[3].axes.set_xlabel('Wavelength (nm)')
            self.canvases[3].axes.set_ylabel('Intensity ')
            self.canvases[3].axes.set_title("Calib E", color='w')
            [t.set_color('w') for t in self.canvases[3].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[3].axes.yaxis.get_ticklabels()]
            self.plot_datas[3] = specDataE_calib
            if self.reference_plots[3] is None:
                plot_refs = self.canvases[3].axes.plot(self.wavelength,specDataE_calib, color=(0,1,0.29), alpha = 0.4)
                self.reference_plots[3] = plot_refs[0]	
            else:
                self.reference_plots[3].set_ydata(specDataE_calib)
                self.reference_plots[3].set_alpha(0.4)
            self.canvases[3].draw()
            wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
        # print(self.wavelength[min(wAB)])
        # print(self.wavelength[max(wAB)])
            min_y = min(specDataE_calib[min(wAB):max(wAB)])
            max_y = max(specDataE_calib[min(wAB):max(wAB)])
            self.canvases[6].axes.clear()
            self.canvases[6].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[6].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
            self.canvases[6].axes.set_xlabel('Wavelength (nm)')
            self.canvases[6].axes.set_ylabel('Intensity ')
            self.canvases[6].axes.set_title("Calib E (A-B)",color='w')
            [t.set_color('w') for t in self.canvases[6].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[6].axes.yaxis.get_ticklabels()]
            self.plot_datas[6] = specDataE_calib
            plot_refs = self.canvases[6].axes.plot(self.wavelength, specDataE_calib, color=(0,1,0.29), alpha = 0.4)
            self.reference_plots[6] = plot_refs[0]	
            self.canvases[6].draw()
            if self.intensity_L_ref is not None:
                self.updateFLD(self.intensity_L_ref, self.intensity_E_ref)
            
    def updateFLD(self, specDataL_calib, specDataE_calib):
        self.Ein_687 = self.getResultsMin(specDataE_calib, self.InRange1Min, self.InRange1Max)
        self.Ein_760 = self.getResultsMin(specDataE_calib, self.InRange2Min, self.InRange2Max)
        self.Eout_left_687 = self.getResultsMax(specDataE_calib, self.OutLeftRange1Min, self.OutLeftRange1Max)
        self.Eout_right_687 = self.getResultsMax(specDataE_calib, self.OutRightRange1Min, self.OutRightRange1Max)
        self.Eout_left_760 = self.getResultsMax(specDataE_calib, self.OutLeftRange2Min, self.OutLeftRange2Max)
        self.Eout_right_760 = self.getResultsMax(specDataE_calib, self.OutRightRange2Min, self.OutRightRange2Max)
        
        self.Lin_687 = self.getResultsMin(specDataL_calib, self.InRange1Min, self.InRange1Max)
        self.Lin_760 = self.getResultsMin(specDataL_calib, self.InRange2Min, self.InRange2Max)
        self.Lout_left_687 = self.getResultsMax(specDataL_calib, self.OutLeftRange1Min, self.OutLeftRange1Max)
        self.Lout_left_760 = self.getResultsMax(specDataL_calib, self.OutLeftRange2Min, self.OutLeftRange2Max)
        self.Lout_right_687 = self.getResultsMax(specDataL_calib, self.OutRightRange1Min, self.OutRightRange1Max)
        self.Lout_right_760 = self.getResultsMax(specDataL_calib, self.OutRightRange2Min, self.OutRightRange2Max)
                
        wL687 = (self.Eout_right_687[0] - self.Ein_687[0])/(self.Eout_right_687[0] - self.Eout_left_687[0])
        wL760 = (self.Eout_right_760[0] - self.Ein_760[0])/(self.Eout_right_760[0] - self.Eout_left_760[0])
        wR687 = (self.Ein_687[0] - self.Eout_left_687[0])/(self.Eout_right_687[0] - self.Eout_left_687[0])
        wR760 = (self.Ein_760[0] - self.Eout_left_760[0])/(self.Eout_right_760[0] - self.Eout_left_760[0])
        
        FLD1 = (((wL687 * self.Eout_left_687[1] + wR687 * self.Eout_right_687[1]) * self.Lin_687[1])-(self.Ein_687[1]*(wL687 * self.Lout_left_687[1] + wR687 * self.Lout_right_687[1])))/((wL687 * self.Eout_left_687[1] + wR687 * self.Eout_right_687[1])-self.Ein_687[1])
        FLD2 = (((wL760 * self.Eout_left_760[1] + wR760 * self.Eout_right_760[1]) * self.Lin_760[1])-(self.Ein_760[1]*(wL760 * self.Lout_left_760[1] + wR760 * self.Lout_right_760[1])))/((wL760 * self.Eout_left_760[1] + wR760 * self.Eout_right_760[1])-self.Ein_760[1])
        
        self.ui.lineEdit_13.setText(str(round(FLD1,3)))
        self.ui.lineEdit_15.setText(str(round(FLD2,3)))     
    def savingCompleted(self):
        self.ui.progressBar.setValue(100)
    def savingFinished(self):
        self.ui.pushButton_19.setEnabled(True)
        self.ui.pushButton_17.setEnabled(True)
        self.ui.pushButton_18.setEnabled(True)
        self.ui.pushButton_20.setEnabled(True)
        
        del self.saver

    def beepSound(self):
        winsound.Beep(500,100)
    def updateProgressBar(self, index):
        self.ui.progressBar.setValue(index)
    def saveSpectraOne(self):
        if self.isStopped is False:
            self.stopWorker()
        self.ui.pushButton_19.setEnabled(False)
        self.ui.pushButton_17.setEnabled(False)
        self.ui.pushButton_18.setEnabled(False)
        self.ui.pushButton_20.setEnabled(False)
        # self.spec.integration_time_micros(5000)
        # time.sleep(1 * self.current_scans_to_avg)
        QtWidgets.QApplication.processEvents()
        time.sleep(self.int_time_L/1000000)
        self.ui.progressBar.setValue(0)
        
        # start saving
        self.ui.progressBar.setMaximum(100)
        self.ui.progressBar.setValue(0)
        if self.comboBox.currentIndex() == 0:
            channelMode = 0
            inteTime1 = self.int_time_L
            inteTime2 = self.int_time_E
            calibCoeff1 = self.calibCoeff_L
            calibCoeff2 = self.calibCoeff_E
        elif self.comboBox.currentIndex() == 1:
            channelMode = 1
            inteTime1 = self.int_time_L
            inteTime2 = inteTime1
            calibCoeff1 = self.calibCoeff_L
            calibCoeff2 = self.calibCoeff_E
        else:
            channelMode = 2
            inteTime1 = self.int_time_E
            inteTime2 = inteTime1
            calibCoeff1 = self.calibCoeff_E
            calibCoeff2 = self.calibCoeff_L
        self.saver = SaveThread2(self.spec, 
                                channelMode,
                                self.serialcomm, 
                                inteTime1,
                                inteTime2, 
                                self.current_scans_to_avg,
                                self.current_scans_to_avg, 
                                1, 
                                self.backgroundIntensity,
                                self.calib_coeff_file_name_E,
                                self.directoryPath, 
                                self.ui.lineEdit_14.text(), 
                                self.save_counter)
        self.saver.startSaving.connect(self.ui.lineEdit_2.setText)
        self.saver.changeLineEdit2.connect(self.ui.lineEdit_2.setText)
        self.saver.setCurrentProgress.connect(self.ui.progressBar.setValue)
        self.saver.finishOneMeasurement.connect(self.beepSound)
        self.saver.succeeded.connect(self.savingCompleted)
        self.saver.succeeded2.connect(self.updatePlotAfterSaving)
        self.saver.finished.connect(self.savingFinished)
        self.save_counter = self.save_counter + 1
        self.saver.start()
    def saveSpectraMultiple(self):
        if self.isStopped is False:
            self.stopWorker()
        self.ui.pushButton_19.setEnabled(False)
        self.ui.pushButton_17.setEnabled(False)
        self.ui.pushButton_18.setEnabled(False)
        self.ui.pushButton_20.setEnabled(False)
        # self.spec.integration_time_micros(5000)
        # time.sleep(1 * self.current_scans_to_avg)
        QtWidgets.QApplication.processEvents()
        time.sleep(self.int_time_L/1000000)
        self.ui.progressBar.setValue(0)
        
        # start saving
        self.ui.progressBar.setMaximum(100)
        self.ui.progressBar.setValue(0)
        if self.comboBox.currentIndex() == 0:
            channelMode = 0
            inteTime1 = self.int_time_L
            inteTime2 = self.int_time_E
            calibCoeff1 = self.calibCoeff_L
            calibCoeff2 = self.calibCoeff_E
        elif self.comboBox.currentIndex() == 1:
            channelMode = 1
            inteTime1 = self.int_time_L
            print("inte Time L:" + str(inteTime1))
            inteTime2 = inteTime1
            calibCoeff1 = self.calibCoeff_L
            calibCoeff2 = self.calibCoeff_E
        else:
            channelMode = 2
            inteTime1 = self.int_time_E
            print("inte Time E:" + str(inteTime1))
            inteTime2 = inteTime1
            calibCoeff1 = self.calibCoeff_E
            calibCoeff2 = self.calibCoeff_L
        print("Create save thread")
        self.saver = SaveThread2(self.spec, 
                                channelMode, 
                                self.serialcomm, 
                                inteTime1, 
                                inteTime2, 
                                self.scans_to_avg_L, 
                                self.scans_to_avg_E, 
                                self.intensity_buffersize, 
                                self.backgroundIntensity, 
                                self.calib_coeff_file_name_E,
                                self.directoryPath, 
                                self.ui.lineEdit_14.text(), 
                                self.save_counter)
        self.saver.succeeded.connect(self.savingCompleted)
        self.saver.changeLineEdit2.connect(self.ui.lineEdit_2.setText)
        self.saver.setCurrentProgress.connect(self.ui.progressBar.setValue)
        self.saver.finishOneMeasurement.connect(self.beepSound)
        self.saver.finished.connect(self.savingFinished)
        self.saver.succeeded2.connect(self.updatePlotAfterSaving)
        self.save_counter = self.save_counter + 1
        self.saver.start()
    

        # self.serialcomm.write('on'.encode())
        # self.ui.lineEdit_2.setText("Radiance saving")
        # time.sleep(2)
        # curr_time_L = datetime.now().strftime("%H:%M:%S:%f")
        # intensityL, dark_temp = self.getSpectra(correct_dark_counts=self.correct_dark_counts, correct_nonlinearity=self.correct_nonlinearity)
        # winsound.Beep(500,100)
        # self.serialcomm.write('off'.encode())
        # self.ui.lineEdit_2.setText("Irradiance saving")
        # time.sleep(2)
        # curr_time_E = datetime.now().strftime("%H:%M:%S:%f")
        # intensityE, dark_temp = self.getSpectra(correct_dark_counts=self.correct_dark_counts, correct_nonlinearity=self.correct_nonlinearity)
        # winsound.Beep(500,100)
        # intensityE_calib = np.multiply(intensityE, self.calibCoeff_E)
        # intensityL_calib = np.multiply(intensityL, self.calibCoeff_L)
        # reflectance = self.getReflectance(intensityE, intensityL)
        # control_info = "Integration time (ms) (L): " + str(self.int_time_L/1000) + ", Integration time (ms) (E): " + str(self.int_time_E/1000) + ", Scans to average (L): " + str(self.scans_to_avg_L) + ", Scans to average (E): " + str(self.scans_to_avg_E) + '\n'
        # header_info = "Wavelength, Time (L), Intensity (L), intensity calibrated (L), Time (L), Intensity (E), Intensity calibrated (L), Background, Reflectance " + control_info
        # filename = self.directoryPath + '\\'+self.ui.lineEdit_14.text() + '_'+self.spec.model+'_'+str(self.save_counter)+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'.txt'
        # outfile = open(filename,'w')
        # outfile.write(header_info)
        # for idx in range(0, len(self.wavelength)):
        #     outfile.write(str(round(self.wavelength[idx],4)) + ',' + curr_time_L + ',' + str(round(intensityL[idx],2)) + ',' + str(round(intensityL_calib[idx],2)) + ',' + curr_time_E + ','+ str(round(intensityE[idx],2)) + ',' + str(round(intensityE_calib[idx],2)) + ',' + str(round(self.backgroundIntensity[idx],2)) + ',' + str(round(reflectance[idx],2)) + '\n')
        # outfile.close()
        # winsound.Beep(1000,300)
        # self.save_counter = self.save_counter + 1
        # # updates plots
        # min_y = np.min(intensityL[1::])
        # max_y = np.max(intensityL[1::])
        # QtWidgets.QApplication.processEvents()
        # self.canvases[1].axes.set_ylim(ymin = min_y, ymax= max_y)
        # self.canvases[1].axes.set_xlabel('Wavelength (nm)')
        # self.canvases[1].axes.set_ylabel('Intensity ')
        # self.canvases[1].axes.set_title("Raw L", color='w')
        # [t.set_color('w') for t in self.canvases[1].axes.xaxis.get_ticklabels()]
        # [t.set_color('w') for t in self.canvases[1].axes.yaxis.get_ticklabels()]
        # self.plot_datas[1] = intensityL
        # if self.reference_plots[1] is None:
        #     plot_refs = self.canvases[1].axes.plot(self.wavelength[1::],intensityL[1::], color=(0,1,0.29), alpha = 1)
        #     self.reference_plots[1] = plot_refs[0]	
        # else:
        #     self.reference_plots[1].set_ydata(intensityL[1::])
        #     self.reference_plots[1].set_alpha(1)
        # self.canvases[1].draw()

        # min_y = np.min(intensityL_calib[1::])
        # max_y = np.max(intensityL_calib[1::])
        # QtWidgets.QApplication.processEvents()
        # self.canvases[4].axes.set_ylim(ymin = min_y, ymax= max_y)
        # self.canvases[4].axes.set_xlabel('Wavelength (nm)')
        # self.canvases[4].axes.set_ylabel('Intensity ')
        # self.canvases[4].axes.set_title("Calib L", color='w')
        # [t.set_color('w') for t in self.canvases[4].axes.xaxis.get_ticklabels()]
        # [t.set_color('w') for t in self.canvases[4].axes.yaxis.get_ticklabels()]
        # print("plot calib after saving")
        # self.plot_datas[4] = intensityL_calib
        # if self.reference_plots[4] is None:
        #     plot_refs = self.canvases[4].axes.plot(self.wavelength,intensityL_calib, color=(0,1,0.29), alpha = 1)
        #     self.reference_plots[4] = plot_refs[0]	
        # else:
        #     self.reference_plots[4].set_ydata(intensityL_calib)
        #     self.reference_plots[4].set_alpha(1)
        # self.canvases[4].draw()
        
        # wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
        # # print(self.wavelength[min(wAB)])
        # # print(self.wavelength[max(wAB)])
        # min_y = min(intensityE_calib[min(wAB):max(wAB)])
        # max_y = max(intensityE_calib[min(wAB):max(wAB)])
        # # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
        # self.canvases[7].axes.clear()
        # self.canvases[7].axes.set_ylim(ymin = min_y, ymax= max_y)
        # self.canvases[7].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
        # self.canvases[7].axes.set_xlabel('Wavelength (nm)')
        # self.canvases[7].axes.set_ylabel('Intensity ')
        # self.canvases[7].axes.set_title("Calib L (A-B)",color='w')
        # [t.set_color('w') for t in self.canvases[7].axes.xaxis.get_ticklabels()]
        # [t.set_color('w') for t in self.canvases[7].axes.yaxis.get_ticklabels()]
        # self.plot_datas[7] = intensityL_calib
        # # self.canvases[7].axes.clear()
        # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],intensityL_calib[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
        # self.canvases[7].draw()


        # min_y = np.min(intensityE[1::])
        # max_y = np.max(intensityE[1::])
        # self.canvases[0].axes.set_ylim(ymin = min_y, ymax= max_y)
        # self.canvases[0].axes.set_xlabel('Wavelength (nm)')
        # self.canvases[0].axes.set_ylabel('Intensity ')
        # self.canvases[0].axes.set_title("Raw E", color='w')
        # [t.set_color('w') for t in self.canvases[0].axes.xaxis.get_ticklabels()]
        # [t.set_color('w') for t in self.canvases[0].axes.yaxis.get_ticklabels()]
        # self.plot_datas[0] = intensityE
        # if self.reference_plots[0] is None:
        #     plot_refs = self.canvases[0].axes.plot(self.wavelength[1::],intensityL[1::], color=(0,1,0.29), alpha = 1)
        #     self.reference_plots[0] = plot_refs[0]	
        # else:
        #     self.reference_plots[0].set_ydata(intensityE[1::])
        #     self.reference_plots[0].set_alpha(1)
        # self.canvases[0].draw()

        # min_y = np.min(intensityE_calib[1::])
        # max_y = np.max(intensityE_calib[1::])
        # self.canvases[3].axes.set_ylim(ymin = min_y, ymax= max_y)
        # self.canvases[3].axes.set_xlabel('Wavelength (nm)')
        # self.canvases[3].axes.set_ylabel('Intensity ')
        # self.canvases[3].axes.set_title("Calib E", color='w')
        # [t.set_color('w') for t in self.canvases[3].axes.xaxis.get_ticklabels()]
        # [t.set_color('w') for t in self.canvases[3].axes.yaxis.get_ticklabels()]
        # self.plot_datas[3] = intensityE_calib
        # if self.reference_plots[3] is None:
        #     plot_refs = self.canvases[3].axes.plot(self.wavelength,intensityE_calib, color=(0,1,0.29), alpha = 1)
        #     self.reference_plots[3] = plot_refs[0]	
        # else:
        #     self.reference_plots[3].set_ydata(intensityE_calib)
        #     self.reference_plots[3].set_alpha(1)
        # self.canvases[3].draw()

        # wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
        # # print(self.wavelength[min(wAB)])
        # # print(self.wavelength[max(wAB)])
        # min_y = min(intensityE_calib[min(wAB):max(wAB)])
        # max_y = max(intensityE_calib[min(wAB):max(wAB)])
        # # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
        # self.canvases[6].axes.clear()
        # self.canvases[6].axes.set_ylim(ymin = min_y, ymax= max_y)
        # self.canvases[6].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
        # self.canvases[6].axes.set_xlabel('Wavelength (nm)')
        # self.canvases[6].axes.set_ylabel('Intensity ')
        # self.canvases[6].axes.set_title("Calib E (A-B)",color='w')
        # [t.set_color('w') for t in self.canvases[6].axes.xaxis.get_ticklabels()]
        # [t.set_color('w') for t in self.canvases[6].axes.yaxis.get_ticklabels()]
        # self.plot_datas[6] = intensityE_calib
        
        # # self.canvases[6].axes.clear()
        # plot_refs = self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)],intensityE_calib[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
        # # if self.reference_plots[6] is None:
        # #     # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29))
        # #     plot_refs = self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)],intensityE_calib[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
        # #     self.reference_plots[6] = plot_refs[0]	
        # # else:
        # #     self.reference_plots[6].set_ydata(intensityE_calib[min(wAB):max(wAB)])
        # #     self.reference_plots[6].set_alpha(1)
        # self.canvases[6].draw()

        # max_y = 10
        # min_y = -10
        # # max_y = np.divide(np.max(self.ydata_calib),np.max(np.multiply(np.subtract(self.intensity_E[1::], self.backgroundIntensity[1::]), self.calibCoeff_E[1::])))
        # # print(min_y)
        # # print(max_y)
        # self.canvases[5].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
        # self.canvases[5].axes.set_xlabel('Wavelength (nm)')
        # self.canvases[5].axes.set_ylabel('Intensity ')
        # self.canvases[5].axes.set_title("Reflectance",color='w')
        # [t.set_color('w') for t in self.canvases[5].axes.xaxis.get_ticklabels()]
        # [t.set_color('w') for t in self.canvases[5].axes.yaxis.get_ticklabels()]
        # self.plot_datas[5] = reflectance[1::]
        # if self.reference_plots[5] is None:
        #     plot_refs = self.canvases[5].axes.plot(self.wavelength[1::],reflectance[1::], color=(0,1,0.29))
        #     self.reference_plots[5] = plot_refs[0]	
        # else:
        #     self.reference_plots[5].set_ydata(reflectance[1::])
        # self.canvases[5].draw()
        # # min_y = min(self.reflectance[min(wAB):max(wAB)])
        # # max_y = max(self.reflectance[min(wAB):max(wAB)])
        # # self.ui.lineEdit_2.setText("Measurement On " + str(max_y) + " " + str(min_y))
        # self.canvases[8].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
        # self.canvases[8].axes.set_xlabel('Wavelength (nm)')
        # self.canvases[8].axes.set_ylabel('Intensity ')
        # self.canvases[8].axes.set_title("Reflectance (A-B)",color='w')
        # [t.set_color('w') for t in self.canvases[8].axes.xaxis.get_ticklabels()]
        # [t.set_color('w') for t in self.canvases[8].axes.yaxis.get_ticklabels()]
        # self.plot_datas[8] = reflectance[min(wAB):max(wAB)]
        # if self.reference_plots[8] is None:
        #     plot_refs = self.canvases[8].axes.plot(self.wavelength[min(wAB):max(wAB)],reflectance[min(wAB):max(wAB)], color=(0,1,0.29))
        #     self.reference_plots[8] = plot_refs[0]	
        # else:
        #     self.reference_plots[8].set_ydata(reflectance[min(wAB):max(wAB)])
        # self.canvases[8].draw()
    def saveSpectra4(self):
        self.stopWorker()
        intensityL_temp_buffer = np.empty([len(self.wavelength), self.intensity_buffersize])
        intensityE_temp_buffer = np.empty([len(self.wavelength), self.intensity_buffersize])
        intenstiyE_temp_time_buffer = []
        intensityL_temp_time_buffer = []
        for i in range(0, self.intensity_buffersize):
            
            self.serialcomm.write('on'.encode())
            time.sleep(2)
            self.ui.lineEdit_2.setText("Radiance channel saving")
            curr_time = datetime.now().strftime("%H:%M:%S:%f")
            intensityL_temp_time_buffer.append(curr_time)
            IntensityL_temp, dark_temp = self.getSpectra(correct_dark_counts = self.correct_dark_counts, correct_nonlinearity=self.correct_nonlinearity)
            intensityL_temp_buffer[:,i] = [a-b for a, b in zip(IntensityL_temp, self.backgroundIntensity)]
            winsound.Beep(500,100)
            
            self.serialcomm.write('off'.encode())
            time.sleep(2)
            self.ui.lineEdit_2.setText("Irradiance channel saving")
            curr_time = datetime.now().strftime("%H:%M:%S:%f")
            intenstiyE_temp_time_buffer.append(curr_time)
            IntensityE_temp, dark_temp = self.getSpectra(correct_dark_counts = self.correct_dark_counts, correct_nonlinearity=self.correct_nonlinearity)
            intensityE_temp_buffer[:,i] = [a-b for a, b in zip(IntensityE_temp, self.backgroundIntensity)]
            winsound.Beep(500,100)
        control_info = "Integration time (L): " + str(self.int_time_L) + ", Integration time (E): " + str(self.int_time_E) + ", Scans to average (L): " + str(self.scans_to_avg_L) + ", Scans to average (E): " + str(self.scans_to_avg_E) + '\n'
        filename = self.directoryPath + '\\'+self.ui.lineEdit_14.text() + '_'+self.spec.model+'_'+str(self.save_counter)+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'.txt'
        outfile = open(filename,'w')
        headerInfo = "Wavelength (nm)" + ","
        # + "Intensity 1 (L)," + "Intensity 1 calibrated (L)," + "Intensity 1 (E)," + "Intensity 1 calibrated (E)," + "Intensity 2 (L)," + "Intensity 2 calibrated (L)," + "Intensity 2 (E)," + "Intensity 2 calibrated (E),"+ "Intensity 3 (L)," + "Intensity 3 calibrated (L),"+ "Intensity 3 (E)," + "Intensity 3 calibrated (E),"+ "Intensity 4 (L)," + "Intensity 4 calibrated (L),"+ "Intensity 4 (E)," + "Intensity 4 calibrated (E),"+ "Intensity 5 (L)," + "Intensity 5 calibrated (L),"+ "Intensity 5 (E)," + "Intensity 5 calibrated (E),"+ "Reflectance," + "Background\n"
        for j in range(0, self.intensity_buffersize):
            headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (L)," + "Intensity "+str(j+1)+" calibrated (L)," 
        for i in range(0, self.intensity_buffersize):
            headerInfo = headerInfo + "Time ("+str(i+1) +")," +"Intensity "+str(i+1)+" (E)," + "Intensity "+str(i+1)+" calibrated (E)," + "Reflectance " + str(i+1)+","
        headerInfo = headerInfo + "Background, " + control_info + "\n"
        outfile.write(headerInfo)
        for n in range(0, len(self.wavelength)):
            lineInput = str(self.wavelength[n]) + ','
            for j in range(0, self.intensity_buffersize):
                intensityE_calib = intensityE_temp_buffer[n,j] * self.calibCoeff_E[n]
                lineInput = lineInput + intenstiyE_temp_time_buffer[j] + ','+ str(round(intensityE_temp_buffer[n,j])) + ',' + str(round(intensityE_calib)) + ','
            for i in range(0, self.intensity_buffersize):
                # intensityL_calib = self.intensity_L_queue[i][n] * self.calibCoeff_L[n]
                intensityL_calib = intensityL_temp_buffer[n,i] * self.calibCoeff_L[n]
                reference_percentage = 100
                if (self.intensity_buffersize == 1):
                    reflectance = intensityL_calib/((intensityE_temp_buffer[n,0] * self.calibCoeff_E[n])/(reference_percentage/100))
                else:
                    reflectance = intensityL_calib/((intensityE_temp_buffer[n,round(self.intensity_buffersize/2)] * self.calibCoeff_E[n])/(reference_percentage/100))
    #             # lineInput = lineInput + str(round(self.intensity_L_queue[i][n])) + ',' + str(round(intensityL_calib)) + ',' + str(round(self.intensity_E_queue[i][n])) + ',' + str(round(intensityE_calib)) + ',' + str(round(reflectance)) + ','
                lineInput = lineInput + intensityL_temp_time_buffer[i] + ',' + str(round(intensityL_temp_buffer[n,i])) + ',' + str(round(intensityL_calib)) + ','  + str(round(reflectance)) + ','
            lineInput = lineInput + str(round(self.backgroundIntensity[n])) + '\n'
            outfile.write(lineInput)
    #     # 
        outfile.close()
        self.save_counter = self.save_counter + 1
        time.sleep(1)
        winsound.Beep(1000,300)
        min_y = np.min(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
        max_y = np.max(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
        QtWidgets.QApplication.processEvents()
        self.canvases[1].axes.set_ylim(ymin = min_y, ymax= max_y)
        self.canvases[1].axes.set_xlabel('Wavelength (nm)')
        self.canvases[1].axes.set_ylabel('Intensity ')
        self.canvases[1].axes.set_title("Raw L", color='w')
        [t.set_color('w') for t in self.canvases[1].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[1].axes.yaxis.get_ticklabels()]
        self.plot_datas[1] = intensityL_temp_buffer[:,self.intensity_buffersize-1]
        if self.reference_plots[1] is None:
            plot_refs = self.canvases[1].axes.plot(self.wavelength[1::],intensityL_temp_buffer[1::,self.intensity_buffersize-1], color=(0,1,0.29), alpha = 1)
            self.reference_plots[1] = plot_refs[0]	
        else:
            self.reference_plots[1].set_ydata(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
            self.reference_plots[1].set_alpha(1)
        self.canvases[1].draw()

        intensityL_calib_temp = np.multiply(intensityL_temp_buffer[:,self.intensity_buffersize-1], self.calibCoeff_L)
        min_y = np.min(intensityL_calib_temp[1::])
        max_y = np.max(intensityL_calib_temp[1::])
        QtWidgets.QApplication.processEvents()
        self.canvases[4].axes.set_ylim(ymin = min_y, ymax= max_y)
        self.canvases[4].axes.set_xlabel('Wavelength (nm)')
        self.canvases[4].axes.set_ylabel('Intensity ')
        self.canvases[4].axes.set_title("Calib L", color='w')
        [t.set_color('w') for t in self.canvases[4].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[4].axes.yaxis.get_ticklabels()]
        self.plot_datas[4] = intensityL_calib_temp
        if self.reference_plots[4] is None:
            plot_refs = self.canvases[4].axes.plot(self.wavelength,intensityL_calib_temp, color=(0,1,0.29), alpha = 1)
            self.reference_plots[4] = plot_refs[0]	
        else:
            self.reference_plots[4].set_ydata(intensityL_calib_temp)
            self.reference_plots[4].set_alpha(1)
        self.canvases[4].draw()
        
        wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
        # print(self.wavelength[min(wAB)])
        # print(self.wavelength[max(wAB)])
        min_y = min(intensityL_calib_temp[min(wAB):max(wAB)])
        max_y = max(intensityL_calib_temp[min(wAB):max(wAB)])
        # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
        self.canvases[7].axes.clear()
        self.canvases[7].axes.set_ylim(ymin = min_y, ymax= max_y)
        self.canvases[7].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
        self.canvases[7].axes.set_xlabel('Wavelength (nm)')
        self.canvases[7].axes.set_ylabel('Intensity ')
        self.canvases[7].axes.set_title("Calib L (A-B)",color='w')
        [t.set_color('w') for t in self.canvases[7].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[7].axes.yaxis.get_ticklabels()]
        self.plot_datas[7] = intensityL_calib_temp
        # self.reference_plots[7] = None
        
        self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityL_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
        # if self.reference_plots[7] is None:
        #     # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29))
        #     plot_refs = self.canvases[7].axes.plot(self.wavelength, intensityL_calib_temp, color=(0,1,0.29), alpha = 1)
        #     self.reference_plots[7] = plot_refs[0]	
        # else:
        #     self.reference_plots[7].set_ydata(intensityL_calib_temp)
        #     self.reference_plots[7].set_alpha(1)
        self.canvases[7].draw()


        min_y = np.min(intensityE_temp_buffer[1::,self.intensity_buffersize-1])
        max_y = np.max(intensityE_temp_buffer[1::, self.intensity_buffersize-1])
        self.canvases[0].axes.set_ylim(ymin = min_y, ymax= max_y)
        self.canvases[0].axes.set_xlabel('Wavelength (nm)')
        self.canvases[0].axes.set_ylabel('Intensity ')
        self.canvases[0].axes.set_title("Raw E", color='w')
        [t.set_color('w') for t in self.canvases[0].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[0].axes.yaxis.get_ticklabels()]
        self.plot_datas[0] = intensityE_temp_buffer[:, self.intensity_buffersize-1]
        if self.reference_plots[0] is None:
            plot_refs = self.canvases[0].axes.plot(self.wavelength[1::],intensityE_temp_buffer[1::, self.intensity_buffersize-1], color=(0,1,0.29), alpha = 1)
            self.reference_plots[0] = plot_refs[0]	
        else:
            self.reference_plots[0].set_ydata(intensityE_temp_buffer[1::, self.intensity_buffersize-1])
            self.reference_plots[0].set_alpha(1)
        self.canvases[0].draw()
        
        intensityE_calib_temp = np.multiply(intensityE_temp_buffer[:,self.intensity_buffersize-1],self.calibCoeff_E)
        min_y = np.min(intensityE_calib_temp[1::])
        max_y = np.max(intensityE_calib_temp[1::])
        self.canvases[3].axes.set_ylim(ymin = min_y, ymax= max_y)
        self.canvases[3].axes.set_xlabel('Wavelength (nm)')
        self.canvases[3].axes.set_ylabel('Intensity ')
        self.canvases[3].axes.set_title("Calib E", color='w')
        [t.set_color('w') for t in self.canvases[3].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[3].axes.yaxis.get_ticklabels()]
        self.plot_datas[3] = intensityE_calib_temp
        if self.reference_plots[3] is None:
            plot_refs = self.canvases[3].axes.plot(self.wavelength,intensityE_calib_temp, color=(0,1,0.29), alpha = 1)
            self.reference_plots[3] = plot_refs[0]	
        else:
            self.reference_plots[3].set_ydata(intensityE_calib_temp)
            self.reference_plots[3].set_alpha(1)
        self.canvases[3].draw()

        wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
        # print(self.wavelength[min(wAB)])
        # print(self.wavelength[max(wAB)])
        min_y = min(intensityE_calib_temp[min(wAB):max(wAB)])
        max_y = max(intensityE_calib_temp[min(wAB):max(wAB)])
        # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
        self.canvases[6].axes.clear()
        self.canvases[6].axes.set_ylim(ymin = min_y, ymax= max_y)
        self.canvases[6].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
        self.canvases[6].axes.set_xlabel('Wavelength (nm)')
        self.canvases[6].axes.set_ylabel('Intensity ')
        self.canvases[6].axes.set_title("Calib E (A-B)",color='w')
        [t.set_color('w') for t in self.canvases[6].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[6].axes.yaxis.get_ticklabels()]
        self.plot_datas[6] = intensityE_calib_temp
        # self.reference_plots[6] = None
        
        self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityE_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
        # if self.reference_plots[6] is None:
        #     # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29))
        #     plot_refs = self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityE_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
        #     self.reference_plots[6] = plot_refs[0]	
        # else:
        #     self.reference_plots[6].set_ydata(intensityE_calib_temp)
        #     self.reference_plots[6].set_alpha(1)
        self.canvases[6].draw()

        max_y = 10
        min_y = -10
        # max_y = np.divide(np.max(self.ydata_calib),np.max(np.multiply(np.subtract(self.intensity_E[1::], self.backgroundIntensity[1::]), self.calibCoeff_E[1::])))
        # print(min_y)
        # print(max_y)
        reflectance_temp = self.getReflectance(intensityE_temp_buffer[:,self.intensity_buffersize-1], intensityL_temp_buffer[:, self.intensity_buffersize-1])
        self.canvases[5].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
        self.canvases[5].axes.set_xlabel('Wavelength (nm)')
        self.canvases[5].axes.set_ylabel('Intensity ')
        self.canvases[5].axes.set_title("Reflectance",color='w')
        [t.set_color('w') for t in self.canvases[5].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[5].axes.yaxis.get_ticklabels()]
        self.plot_datas[5] = reflectance_temp[1::]
        if self.reference_plots[5] is None:
            plot_refs = self.canvases[5].axes.plot(self.wavelength[1::],reflectance_temp[1::], color=(0,1,0.29))
            self.reference_plots[5] = plot_refs[0]	
        else:
            self.reference_plots[5].set_ydata(reflectance_temp[1::])
        self.canvases[5].draw()
        # min_y = min(self.reflectance[min(wAB):max(wAB)])
        # max_y = max(self.reflectance[min(wAB):max(wAB)])
        # self.ui.lineEdit_2.setText("Measurement On " + str(max_y) + " " + str(min_y))
        self.canvases[8].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
        self.canvases[8].axes.set_xlabel('Wavelength (nm)')
        self.canvases[8].axes.set_ylabel('Intensity ')
        self.canvases[8].axes.set_title("Reflectance (A-B)",color='w')
        [t.set_color('w') for t in self.canvases[8].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[8].axes.yaxis.get_ticklabels()]
        self.plot_datas[8] = reflectance_temp[min(wAB):max(wAB)]
        if self.reference_plots[8] is None:
            plot_refs = self.canvases[8].axes.plot(self.wavelength[min(wAB):max(wAB)],reflectance_temp[min(wAB):max(wAB)], color=(0,1,0.29))
            self.reference_plots[8] = plot_refs[0]	
        else:
            self.reference_plots[8].set_ydata(reflectance_temp[min(wAB):max(wAB)])
        self.canvases[8].draw()
    def saveSpectra5(self):
        self.stopWorker()
        if self.ui.comboBox.currentIndex() == 0:
            intensityL_temp_buffer = np.empty([len(self.wavelength), self.intensity_buffersize])
            intensityE_temp_buffer = np.empty([len(self.wavelength), self.intensity_buffersize])
            intenstiyE_temp_time_buffer = []
            intensityL_temp_time_buffer = []
            for i in range(0, self.intensity_buffersize):
                
                self.serialcomm.write('on'.encode())
                time.sleep(2)
                self.ui.lineEdit_2.setText("Radiance channel saving")
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                intensityL_temp_time_buffer.append(curr_time)
                IntensityL_temp, dark_temp = self.getSpectra(correct_dark_counts = self.correct_dark_counts, correct_nonlinearity=self.correct_nonlinearity)
                intensityL_temp_buffer[:,i] = [a-b for a, b in zip(IntensityL_temp, self.backgroundIntensity)]
                winsound.Beep(500,100)
                
                self.serialcomm.write('off'.encode())
                time.sleep(2)
                self.ui.lineEdit_2.setText("Irradiance channel saving")
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                intenstiyE_temp_time_buffer.append(curr_time)
                IntensityE_temp, dark_temp = self.getSpectra(correct_dark_counts = self.correct_dark_counts, correct_nonlinearity=self.correct_nonlinearity)
                intensityE_temp_buffer[:,i] = [a-b for a, b in zip(IntensityE_temp, self.backgroundIntensity)]
                winsound.Beep(500,100)
            control_info = "Integration time (L): " + str(self.int_time_L) + ", Integration time (E): " + str(self.int_time_E) + ", Scans to average (L): " + str(self.scans_to_avg_L) + ", Scans to average (E): " + str(self.scans_to_avg_E) + '\n'
            filename = self.directoryPath + '\\'+self.ui.lineEdit_14.text() + '_'+self.spec.model+'_'+str(self.save_counter)+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'.txt'
            outfile = open(filename,'w')
            headerInfo = "Wavelength (nm)" + ","
            # + "Intensity 1 (L)," + "Intensity 1 calibrated (L)," + "Intensity 1 (E)," + "Intensity 1 calibrated (E)," + "Intensity 2 (L)," + "Intensity 2 calibrated (L)," + "Intensity 2 (E)," + "Intensity 2 calibrated (E),"+ "Intensity 3 (L)," + "Intensity 3 calibrated (L),"+ "Intensity 3 (E)," + "Intensity 3 calibrated (E),"+ "Intensity 4 (L)," + "Intensity 4 calibrated (L),"+ "Intensity 4 (E)," + "Intensity 4 calibrated (E),"+ "Intensity 5 (L)," + "Intensity 5 calibrated (L),"+ "Intensity 5 (E)," + "Intensity 5 calibrated (E),"+ "Reflectance," + "Background\n"
            for j in range(0, self.intensity_buffersize):
                headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (L)," + "Intensity "+str(j+1)+" calibrated (L)," 
            for i in range(0, self.intensity_buffersize):
                headerInfo = headerInfo + "Time ("+str(i+1) +")," +"Intensity "+str(i+1)+" (E)," + "Intensity "+str(i+1)+" calibrated (E)," + "Reflectance " + str(i+1)+","
            headerInfo = headerInfo + "Background, " + control_info + "\n"
            outfile.write(headerInfo)
            for n in range(0, len(self.wavelength)):
                lineInput = str(self.wavelength[n]) + ','
                for j in range(0, self.intensity_buffersize):
                    intensityE_calib = intensityE_temp_buffer[n,j] * self.calibCoeff_E[n]
                    lineInput = lineInput + intenstiyE_temp_time_buffer[j] + ','+ str(round(intensityE_temp_buffer[n,j])) + ',' + str(round(intensityE_calib)) + ','
                for i in range(0, self.intensity_buffersize):
                    # intensityL_calib = self.intensity_L_queue[i][n] * self.calibCoeff_L[n]
                    intensityL_calib = intensityL_temp_buffer[n,i] * self.calibCoeff_L[n]
                    reference_percentage = 100
                    if (self.intensity_buffersize == 1):
                        reflectance = intensityL_calib/((intensityE_temp_buffer[n,0] * self.calibCoeff_E[n])/(reference_percentage/100))
                    else:
                        reflectance = intensityL_calib/((intensityE_temp_buffer[n,round(self.intensity_buffersize/2)] * self.calibCoeff_E[n])/(reference_percentage/100))
        #             # lineInput = lineInput + str(round(self.intensity_L_queue[i][n])) + ',' + str(round(intensityL_calib)) + ',' + str(round(self.intensity_E_queue[i][n])) + ',' + str(round(intensityE_calib)) + ',' + str(round(reflectance)) + ','
                    lineInput = lineInput + intensityL_temp_time_buffer[i] + ',' + str(round(intensityL_temp_buffer[n,i])) + ',' + str(round(intensityL_calib)) + ','  + str(round(reflectance)) + ','
                lineInput = lineInput + str(round(self.backgroundIntensity[n])) + '\n'
                outfile.write(lineInput)
        #     # 
            outfile.close()
            self.save_counter = self.save_counter + 1
            time.sleep(1)
            winsound.Beep(1000,300)
            min_y = np.min(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
            max_y = np.max(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
            QtWidgets.QApplication.processEvents()
            self.canvases[1].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[1].axes.set_xlabel('Wavelength (nm)')
            self.canvases[1].axes.set_ylabel('Intensity ')
            self.canvases[1].axes.set_title("Raw L", color='w')
            [t.set_color('w') for t in self.canvases[1].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[1].axes.yaxis.get_ticklabels()]
            self.plot_datas[1] = intensityL_temp_buffer[:,self.intensity_buffersize-1]
            if self.reference_plots[1] is None:
                plot_refs = self.canvases[1].axes.plot(self.wavelength[1::],intensityL_temp_buffer[1::,self.intensity_buffersize-1], color=(0,1,0.29), alpha = 1)
                self.reference_plots[1] = plot_refs[0]	
            else:
                self.reference_plots[1].set_ydata(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
                self.reference_plots[1].set_alpha(1)
            self.canvases[1].draw()

            intensityL_calib_temp = np.multiply(intensityL_temp_buffer[:,self.intensity_buffersize-1], self.calibCoeff_L)
            min_y = np.min(intensityL_calib_temp[1::])
            max_y = np.max(intensityL_calib_temp[1::])
            QtWidgets.QApplication.processEvents()
            self.canvases[4].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[4].axes.set_xlabel('Wavelength (nm)')
            self.canvases[4].axes.set_ylabel('Intensity ')
            self.canvases[4].axes.set_title("Calib L", color='w')
            [t.set_color('w') for t in self.canvases[4].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[4].axes.yaxis.get_ticklabels()]
            self.plot_datas[4] = intensityL_calib_temp
            if self.reference_plots[4] is None:
                plot_refs = self.canvases[4].axes.plot(self.wavelength,intensityL_calib_temp, color=(0,1,0.29), alpha = 1)
                self.reference_plots[4] = plot_refs[0]	
            else:
                self.reference_plots[4].set_ydata(intensityL_calib_temp)
                self.reference_plots[4].set_alpha(1)
            self.canvases[4].draw()
            
            wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
            # print(self.wavelength[min(wAB)])
            # print(self.wavelength[max(wAB)])
            min_y = min(intensityL_calib_temp[min(wAB):max(wAB)])
            max_y = max(intensityL_calib_temp[min(wAB):max(wAB)])
            # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
            self.canvases[7].axes.clear()
            self.canvases[7].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[7].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
            self.canvases[7].axes.set_xlabel('Wavelength (nm)')
            self.canvases[7].axes.set_ylabel('Intensity ')
            self.canvases[7].axes.set_title("Calib L (A-B)",color='w')
            [t.set_color('w') for t in self.canvases[7].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[7].axes.yaxis.get_ticklabels()]
            self.plot_datas[7] = intensityL_calib_temp
            # self.reference_plots[7] = None
            
            self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityL_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
            # if self.reference_plots[7] is None:
            #     # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29))
            #     plot_refs = self.canvases[7].axes.plot(self.wavelength, intensityL_calib_temp, color=(0,1,0.29), alpha = 1)
            #     self.reference_plots[7] = plot_refs[0]	
            # else:
            #     self.reference_plots[7].set_ydata(intensityL_calib_temp)
            #     self.reference_plots[7].set_alpha(1)
            self.canvases[7].draw()


            min_y = np.min(intensityE_temp_buffer[1::,self.intensity_buffersize-1])
            max_y = np.max(intensityE_temp_buffer[1::, self.intensity_buffersize-1])
            self.canvases[0].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[0].axes.set_xlabel('Wavelength (nm)')
            self.canvases[0].axes.set_ylabel('Intensity ')
            self.canvases[0].axes.set_title("Raw E", color='w')
            [t.set_color('w') for t in self.canvases[0].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[0].axes.yaxis.get_ticklabels()]
            self.plot_datas[0] = intensityE_temp_buffer[:, self.intensity_buffersize-1]
            if self.reference_plots[0] is None:
                plot_refs = self.canvases[0].axes.plot(self.wavelength[1::],intensityE_temp_buffer[1::, self.intensity_buffersize-1], color=(0,1,0.29), alpha = 1)
                self.reference_plots[0] = plot_refs[0]	
            else:
                self.reference_plots[0].set_ydata(intensityE_temp_buffer[1::, self.intensity_buffersize-1])
                self.reference_plots[0].set_alpha(1)
            self.canvases[0].draw()
            
            intensityE_calib_temp = np.multiply(intensityE_temp_buffer[:,self.intensity_buffersize-1],self.calibCoeff_E)
            min_y = np.min(intensityE_calib_temp[1::])
            max_y = np.max(intensityE_calib_temp[1::])
            self.canvases[3].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[3].axes.set_xlabel('Wavelength (nm)')
            self.canvases[3].axes.set_ylabel('Intensity ')
            self.canvases[3].axes.set_title("Calib E", color='w')
            [t.set_color('w') for t in self.canvases[3].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[3].axes.yaxis.get_ticklabels()]
            self.plot_datas[3] = intensityE_calib_temp
            if self.reference_plots[3] is None:
                plot_refs = self.canvases[3].axes.plot(self.wavelength,intensityE_calib_temp, color=(0,1,0.29), alpha = 1)
                self.reference_plots[3] = plot_refs[0]	
            else:
                self.reference_plots[3].set_ydata(intensityE_calib_temp)
                self.reference_plots[3].set_alpha(1)
            self.canvases[3].draw()

            wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
            # print(self.wavelength[min(wAB)])
            # print(self.wavelength[max(wAB)])
            min_y = min(intensityE_calib_temp[min(wAB):max(wAB)])
            max_y = max(intensityE_calib_temp[min(wAB):max(wAB)])
            # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
            self.canvases[6].axes.clear()
            self.canvases[6].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[6].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
            self.canvases[6].axes.set_xlabel('Wavelength (nm)')
            self.canvases[6].axes.set_ylabel('Intensity ')
            self.canvases[6].axes.set_title("Calib E (A-B)",color='w')
            [t.set_color('w') for t in self.canvases[6].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[6].axes.yaxis.get_ticklabels()]
            self.plot_datas[6] = intensityE_calib_temp
            # self.reference_plots[6] = None
            
            self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityE_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
            # if self.reference_plots[6] is None:
            #     # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29))
            #     plot_refs = self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityE_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
            #     self.reference_plots[6] = plot_refs[0]	
            # else:
            #     self.reference_plots[6].set_ydata(intensityE_calib_temp)
            #     self.reference_plots[6].set_alpha(1)
            self.canvases[6].draw()

            max_y = 10
            min_y = -10
            # max_y = np.divide(np.max(self.ydata_calib),np.max(np.multiply(np.subtract(self.intensity_E[1::], self.backgroundIntensity[1::]), self.calibCoeff_E[1::])))
            # print(min_y)
            # print(max_y)
            reflectance_temp = self.getReflectance(intensityE_temp_buffer[:,self.intensity_buffersize-1], intensityL_temp_buffer[:, self.intensity_buffersize-1])
            self.canvases[5].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
            self.canvases[5].axes.set_xlabel('Wavelength (nm)')
            self.canvases[5].axes.set_ylabel('Intensity ')
            self.canvases[5].axes.set_title("Reflectance",color='w')
            [t.set_color('w') for t in self.canvases[5].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[5].axes.yaxis.get_ticklabels()]
            self.plot_datas[5] = reflectance_temp[1::]
            if self.reference_plots[5] is None:
                plot_refs = self.canvases[5].axes.plot(self.wavelength[1::],reflectance_temp[1::], color=(0,1,0.29))
                self.reference_plots[5] = plot_refs[0]	
            else:
                self.reference_plots[5].set_ydata(reflectance_temp[1::])
            self.canvases[5].draw()
            # min_y = min(self.reflectance[min(wAB):max(wAB)])
            # max_y = max(self.reflectance[min(wAB):max(wAB)])
            # self.ui.lineEdit_2.setText("Measurement On " + str(max_y) + " " + str(min_y))
            self.canvases[8].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
            self.canvases[8].axes.set_xlabel('Wavelength (nm)')
            self.canvases[8].axes.set_ylabel('Intensity ')
            self.canvases[8].axes.set_title("Reflectance (A-B)",color='w')
            [t.set_color('w') for t in self.canvases[8].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[8].axes.yaxis.get_ticklabels()]
            self.plot_datas[8] = reflectance_temp[min(wAB):max(wAB)]
            if self.reference_plots[8] is None:
                plot_refs = self.canvases[8].axes.plot(self.wavelength[min(wAB):max(wAB)],reflectance_temp[min(wAB):max(wAB)], color=(0,1,0.29))
                self.reference_plots[8] = plot_refs[0]	
            else:
                self.reference_plots[8].set_ydata(reflectance_temp[min(wAB):max(wAB)])
            self.canvases[8].draw()
        elif self.ui.comboBox.currentIndex() == 1:
            self.serialcomm.write('on'.encode())
            time.sleep(2)
            intensityL_temp_buffer = np.empty([len(self.wavelength), self.intensity_buffersize])
            intensityL_temp_time_buffer = []
            for i in range(0, self.intensity_buffersize):
                self.ui.lineEdit_2.setText("Radiance channel saving")
                curr_time = datetime.now().strftime("%H:%M:%S:%f")
                intensityL_temp_time_buffer.append(curr_time)
                IntensityL_temp, dark_temp = self.getSpectra(correct_dark_counts = self.correct_dark_counts, correct_nonlinearity=self.correct_nonlinearity)
                intensityL_temp_buffer[:,i] = [a-b for a, b in zip(IntensityL_temp, self.backgroundIntensity)]
                winsound.Beep(500,100)
                time.sleep(2)
                self.ui.lineEdit_2.setText("Irradiance channel saving")
            control_info = "Integration time (L): " + str(self.int_time_L) +  ", Scans to average (L): " + str(self.scans_to_avg_L) + '\n'
            filename = self.directoryPath + '\\'+self.ui.lineEdit_14.text() + '_'+self.spec.model+'_'+str(self.save_counter)+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'.txt'
            outfile = open(filename,'w')
            headerInfo = "Wavelength (nm)" + ","
            # + "Intensity 1 (L)," + "Intensity 1 calibrated (L)," + "Intensity 1 (E)," + "Intensity 1 calibrated (E)," + "Intensity 2 (L)," + "Intensity 2 calibrated (L)," + "Intensity 2 (E)," + "Intensity 2 calibrated (E),"+ "Intensity 3 (L)," + "Intensity 3 calibrated (L),"+ "Intensity 3 (E)," + "Intensity 3 calibrated (E),"+ "Intensity 4 (L)," + "Intensity 4 calibrated (L),"+ "Intensity 4 (E)," + "Intensity 4 calibrated (E),"+ "Intensity 5 (L)," + "Intensity 5 calibrated (L),"+ "Intensity 5 (E)," + "Intensity 5 calibrated (E),"+ "Reflectance," + "Background\n"
            for j in range(0, self.intensity_buffersize):
                headerInfo = headerInfo + "Time ("+str(j+1) +")," + "Intensity "+str(j+1)+" (L)," + "Intensity "+str(j+1)+" calibrated (L)," 
            headerInfo = headerInfo + "Background, " + control_info + "\n"
            outfile.write(headerInfo)
            for n in range(0, len(self.wavelength)):
                lineInput = str(self.wavelength[n]) + ','
                for i in range(0, self.intensity_buffersize):
                    # intensityL_calib = self.intensity_L_queue[i][n] * self.calibCoeff_L[n]
                    intensityL_calib = intensityL_temp_buffer[n,i] * self.calibCoeff_L[n]
                    reference_percentage = 100
                    if (self.intensity_buffersize == 1):
                        reflectance = intensityL_calib/((intensityE_temp_buffer[n,0] * self.calibCoeff_E[n])/(reference_percentage/100))
                    else:
                        reflectance = intensityL_calib/((intensityE_temp_buffer[n,round(self.intensity_buffersize/2)] * self.calibCoeff_E[n])/(reference_percentage/100))
        #             # lineInput = lineInput + str(round(self.intensity_L_queue[i][n])) + ',' + str(round(intensityL_calib)) + ',' + str(round(self.intensity_E_queue[i][n])) + ',' + str(round(intensityE_calib)) + ',' + str(round(reflectance)) + ','
                    lineInput = lineInput + intensityL_temp_time_buffer[i] + ',' + str(round(intensityL_temp_buffer[n,i])) + ',' + str(round(intensityL_calib)) + ','  + str(round(reflectance)) + ','
                lineInput = lineInput + str(round(self.backgroundIntensity[n])) + '\n'
                outfile.write(lineInput)
        #     # 
            outfile.close()
            self.save_counter = self.save_counter + 1
            time.sleep(1)
            winsound.Beep(1000,300)
            min_y = np.min(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
            max_y = np.max(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
            QtWidgets.QApplication.processEvents()
            self.canvases[1].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[1].axes.set_xlabel('Wavelength (nm)')
            self.canvases[1].axes.set_ylabel('Intensity ')
            self.canvases[1].axes.set_title("Raw L", color='w')
            [t.set_color('w') for t in self.canvases[1].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[1].axes.yaxis.get_ticklabels()]
            self.plot_datas[1] = intensityL_temp_buffer[:,self.intensity_buffersize-1]
            if self.reference_plots[1] is None:
                plot_refs = self.canvases[1].axes.plot(self.wavelength[1::],intensityL_temp_buffer[1::,self.intensity_buffersize-1], color=(0,1,0.29), alpha = 1)
                self.reference_plots[1] = plot_refs[0]	
            else:
                self.reference_plots[1].set_ydata(intensityL_temp_buffer[1::,self.intensity_buffersize-1])
                self.reference_plots[1].set_alpha(1)
            self.canvases[1].draw()

            intensityL_calib_temp = np.multiply(intensityL_temp_buffer[:,self.intensity_buffersize-1], self.calibCoeff_L)
            min_y = np.min(intensityL_calib_temp[1::])
            max_y = np.max(intensityL_calib_temp[1::])
            QtWidgets.QApplication.processEvents()
            self.canvases[4].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[4].axes.set_xlabel('Wavelength (nm)')
            self.canvases[4].axes.set_ylabel('Intensity ')
            self.canvases[4].axes.set_title("Calib L", color='w')
            [t.set_color('w') for t in self.canvases[4].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[4].axes.yaxis.get_ticklabels()]
            self.plot_datas[4] = intensityL_calib_temp
            if self.reference_plots[4] is None:
                plot_refs = self.canvases[4].axes.plot(self.wavelength,intensityL_calib_temp, color=(0,1,0.29), alpha = 1)
                self.reference_plots[4] = plot_refs[0]	
            else:
                self.reference_plots[4].set_ydata(intensityL_calib_temp)
                self.reference_plots[4].set_alpha(1)
            self.canvases[4].draw()
            
            wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
            # print(self.wavelength[min(wAB)])
            # print(self.wavelength[max(wAB)])
            min_y = min(intensityL_calib_temp[min(wAB):max(wAB)])
            max_y = max(intensityL_calib_temp[min(wAB):max(wAB)])
            # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
            self.canvases[7].axes.clear()
            self.canvases[7].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[7].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
            self.canvases[7].axes.set_xlabel('Wavelength (nm)')
            self.canvases[7].axes.set_ylabel('Intensity ')
            self.canvases[7].axes.set_title("Calib L (A-B)",color='w')
            [t.set_color('w') for t in self.canvases[7].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[7].axes.yaxis.get_ticklabels()]
            self.plot_datas[7] = intensityL_calib_temp
            # self.reference_plots[7] = None
            
            self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityL_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
            # if self.reference_plots[7] is None:
            #     # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29))
            #     plot_refs = self.canvases[7].axes.plot(self.wavelength, intensityL_calib_temp, color=(0,1,0.29), alpha = 1)
            #     self.reference_plots[7] = plot_refs[0]	
            # else:
            #     self.reference_plots[7].set_ydata(intensityL_calib_temp)
            #     self.reference_plots[7].set_alpha(1)
            self.canvases[7].draw()


            min_y = np.min(intensityE_temp_buffer[1::,self.intensity_buffersize-1])
            max_y = np.max(intensityE_temp_buffer[1::, self.intensity_buffersize-1])
            self.canvases[0].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[0].axes.set_xlabel('Wavelength (nm)')
            self.canvases[0].axes.set_ylabel('Intensity ')
            self.canvases[0].axes.set_title("Raw E", color='w')
            [t.set_color('w') for t in self.canvases[0].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[0].axes.yaxis.get_ticklabels()]
            self.plot_datas[0] = intensityE_temp_buffer[:, self.intensity_buffersize-1]
            if self.reference_plots[0] is None:
                plot_refs = self.canvases[0].axes.plot(self.wavelength[1::],intensityE_temp_buffer[1::, self.intensity_buffersize-1], color=(0,1,0.29), alpha = 1)
                self.reference_plots[0] = plot_refs[0]	
            else:
                self.reference_plots[0].set_ydata(intensityE_temp_buffer[1::, self.intensity_buffersize-1])
                self.reference_plots[0].set_alpha(1)
            self.canvases[0].draw()
            
            intensityE_calib_temp = np.multiply(intensityE_temp_buffer[:,self.intensity_buffersize-1],self.calibCoeff_E)
            min_y = np.min(intensityE_calib_temp[1::])
            max_y = np.max(intensityE_calib_temp[1::])
            self.canvases[3].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[3].axes.set_xlabel('Wavelength (nm)')
            self.canvases[3].axes.set_ylabel('Intensity ')
            self.canvases[3].axes.set_title("Calib E", color='w')
            [t.set_color('w') for t in self.canvases[3].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[3].axes.yaxis.get_ticklabels()]
            self.plot_datas[3] = intensityE_calib_temp
            if self.reference_plots[3] is None:
                plot_refs = self.canvases[3].axes.plot(self.wavelength,intensityE_calib_temp, color=(0,1,0.29), alpha = 1)
                self.reference_plots[3] = plot_refs[0]	
            else:
                self.reference_plots[3].set_ydata(intensityE_calib_temp)
                self.reference_plots[3].set_alpha(1)
            self.canvases[3].draw()

            wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
            # print(self.wavelength[min(wAB)])
            # print(self.wavelength[max(wAB)])
            min_y = min(intensityE_calib_temp[min(wAB):max(wAB)])
            max_y = max(intensityE_calib_temp[min(wAB):max(wAB)])
            # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
            self.canvases[6].axes.clear()
            self.canvases[6].axes.set_ylim(ymin = min_y, ymax= max_y)
            self.canvases[6].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
            self.canvases[6].axes.set_xlabel('Wavelength (nm)')
            self.canvases[6].axes.set_ylabel('Intensity ')
            self.canvases[6].axes.set_title("Calib E (A-B)",color='w')
            [t.set_color('w') for t in self.canvases[6].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[6].axes.yaxis.get_ticklabels()]
            self.plot_datas[6] = intensityE_calib_temp
            # self.reference_plots[6] = None
            
            self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityE_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
            # if self.reference_plots[6] is None:
            #     # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29))
            #     plot_refs = self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)], intensityE_calib_temp[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
            #     self.reference_plots[6] = plot_refs[0]	
            # else:
            #     self.reference_plots[6].set_ydata(intensityE_calib_temp)
            #     self.reference_plots[6].set_alpha(1)
            self.canvases[6].draw()

            max_y = 10
            min_y = -10
            # max_y = np.divide(np.max(self.ydata_calib),np.max(np.multiply(np.subtract(self.intensity_E[1::], self.backgroundIntensity[1::]), self.calibCoeff_E[1::])))
            # print(min_y)
            # print(max_y)
            reflectance_temp = self.getReflectance(intensityE_temp_buffer[:,self.intensity_buffersize-1], intensityL_temp_buffer[:, self.intensity_buffersize-1])
            self.canvases[5].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
            self.canvases[5].axes.set_xlabel('Wavelength (nm)')
            self.canvases[5].axes.set_ylabel('Intensity ')
            self.canvases[5].axes.set_title("Reflectance",color='w')
            [t.set_color('w') for t in self.canvases[5].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[5].axes.yaxis.get_ticklabels()]
            self.plot_datas[5] = reflectance_temp[1::]
            if self.reference_plots[5] is None:
                plot_refs = self.canvases[5].axes.plot(self.wavelength[1::],reflectance_temp[1::], color=(0,1,0.29))
                self.reference_plots[5] = plot_refs[0]	
            else:
                self.reference_plots[5].set_ydata(reflectance_temp[1::])
            self.canvases[5].draw()
            # min_y = min(self.reflectance[min(wAB):max(wAB)])
            # max_y = max(self.reflectance[min(wAB):max(wAB)])
            # self.ui.lineEdit_2.setText("Measurement On " + str(max_y) + " " + str(min_y))
            self.canvases[8].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
            self.canvases[8].axes.set_xlabel('Wavelength (nm)')
            self.canvases[8].axes.set_ylabel('Intensity ')
            self.canvases[8].axes.set_title("Reflectance (A-B)",color='w')
            [t.set_color('w') for t in self.canvases[8].axes.xaxis.get_ticklabels()]
            [t.set_color('w') for t in self.canvases[8].axes.yaxis.get_ticklabels()]
            self.plot_datas[8] = reflectance_temp[min(wAB):max(wAB)]
            if self.reference_plots[8] is None:
                plot_refs = self.canvases[8].axes.plot(self.wavelength[min(wAB):max(wAB)],reflectance_temp[min(wAB):max(wAB)], color=(0,1,0.29))
                self.reference_plots[8] = plot_refs[0]	
            else:
                self.reference_plots[8].set_ydata(reflectance_temp[min(wAB):max(wAB)])
            self.canvases[8].draw()
               
   
    def initializeSpectrometer(self):        
        if self.SpectrometerIndicator.value == False:
            self.ui.lineEdit_2.setText("Spectrometer is initializing")
            self.ui.pushButton_11.setEnabled(False)
            # self.spec = sb.initalizeOceanOptics() #Establishes communication with the spectrometer
            devices = sb.list_devices()
            if(len(devices) == 0):
                self.ui.lineEdit_2.setText("Initialization failed, please connect a device")
            self.spec = sb.Spectrometer(devices[0])
            self.device_list.append(self.spec.model)
            # self.serialcomm = serial.Serial(port,9600)
            # self.serialcomm.timeout = 1
            # self.serialcomm.write('on'.encode())
            self.ui.comboBox_2.addItems(self.device_list)
            self.ui.comboBox_2.setCurrentIndex(0)
            # for x in range(1,5):
            #     time.sleep(0.5)
            #     self.ui.progressBar.setValue(int(x/4*100))
            self.SpectrometerIndicator.value = True
            # if self.if_L:
            #     self.ui.groupBox.setEnabled(True)
            # else:
            #     self.ui.groupBox_2.setEnabled(True)
            
            self.ui.lineEdit_2.setText(self.spec.model + " is ready to go")
            self.ui.pushButton_11.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
            
            # set integration time
            self.ui.spinBox.setMinimum(int(self.spec.integration_time_micros_limits[0]/1000))
            self.ui.spinBox.setMaximum(int(self.spec.integration_time_micros_limits[1]/1000))
            self.ui.spinBox.setValue(5)
            self.int_time_L = 5000
            self.ui.spinBox_4.setMinimum(int(self.spec.integration_time_micros_limits[0]/1000))
            self.ui.spinBox_4.setMaximum(int(self.spec.integration_time_micros_limits[1]/1000))
            self.ui.spinBox_4.setValue(5)
            self.int_time_E = 5000
            # set scans to avg time
            self.ui.spinBox_2.setMinimum(1)
            self.ui.spinBox_2.setMaximum(1000000)
            self.ui.spinBox_2.setValue(10)
            self.scans_to_avg_L = 1
            self.ui.spinBox_5.setMinimum(1)
            self.ui.spinBox_5.setMaximum(1000000)
            self.ui.spinBox_5.setValue(10)
            self.scans_to_avg_E = 1
            # print("maximum intensity: " + str(self.spec.max_intensity))
            self.wavelength = self.spec.wavelengths()
            self.wminmax = [index for index,value in enumerate(self.wavelength) if (value > min(self.wavelength) + 3 and value < max(self.wavelength) - 2)]
                    
            ####### default measurement #######
            self.isIntTimeChanged = False
            self.a_L = None
            self.a_E = None
            self.b_L = None
            self.b_E = None
            if self.ui.comboBox.currentIndex() == 0:
                self.BothFibreMode()
            elif self.ui.comboBox.currentIndex() == 1:
                self.LOnlyFibreMode()
            else:
                self.EOnlyFibreMode()
            self.setSpecIntTime()
            self.setScansToAvg()
            print(self.if_L)
            if self.if_L:
                self.updateRate = self.int_time_L/1000 * self.scans_to_avg_L
                self.current_scans_to_avg = self.scans_to_avg_L
            else:
                self.updateRate = self.int_time_E/1000 * self.scans_to_avg_E
                self.current_scans_to_avg = self.scans_to_avg_E
            # self.timer.setInterval(self.updateRate)
            # E measurements
            # self.ui.pushButton_22.setEnabled(True)
            # self.ui.spinBox_6.setMinimum(1)
            # self.ui.spinBox_6.setMaximum(50)
            # self.ui.spinBox_6.setValue(5)
            
            # L measurements
            self.ui.pushButton_23.setEnabled(True)
            self.ui.spinBox_3.setMinimum(1)
            self.ui.spinBox_3.setMaximum(50)
            self.ui.spinBox_3.setValue(1)
            # self.setMeasNum()
            # self.intensity_E_buffersize = self.ui.spinBox_3.value()
            
            self.intensity_buffersize = self.ui.spinBox_3.value()
            # self.intensity_L_queue = []
            # for i in range(0, self.intensity_buffersize):
            #     self.intensity_L_queue.append([0] * len(self.wavelength))
            # self.intensity_E_queue = []
            # self.intensity_E_time_queue = []
            # for i in range(0, self.intensity_buffersize):
            #     self.intensity_E_time_queue.append("")
            #     self.intensity_E_queue.append([0] * len(self.wavelength))
            
            ########## lineEdits for showing the current channel and number of measurements #########
            if (self.if_L):
                self.ui.lineEdit_4.setText("Current channel: Radiance (L).")
                self.ui.lineEdit_4.setEnabled(False)
            else:
                self.ui.lineEdit_4.setText("Current channel: Irradiance (E).")
                self.ui.lineEdit_4.setEnabled(False)
            
            if self.comboBox.currentIndex() == 0:
                self.ui.lineEdit_5.setText("Number of Meas: " + str(self.intensity_buffersize) + " (L), " + str(self.intensity_buffersize) + " (E).")
            elif self.comboBox.currentIndex() == 1:
                self.ui.lineEdit_5.setText("Current fibre channel: L. Number of Meas: " + str(self.intensity_buffersize))
            else:
                self.ui.lineEdit_5.setText("Current fibre channel: E. Number of Meas: " + str(self.intensity_buffersize))

            self.backgroundIntensity = [0] * len(self.wavelength)
            self.reflectance = [0] * len(self.wavelength)
            self.Eout_avg = 0
            self.Ein_687 = [0,0]
            self.Ein_760 = [0,0]
            self.Eout_left_687 = [0,0]
            self.Eout_right_687 = [0,0]
            self.Eout_left_760 = [0,0]
            self.Eout_right_760 = [0,0]

            self.Lout_avg = 0
            self.Lin_687 = [0,0]
            self.Lin_760 = [0,0]
            self.Lout_left_687 = [0,0]
            self.Lout_right_687 = [0,0]
            self.Lout_left_760 = [0,0]
            self.Lout_right_760 = [0,0]
            # self.backgroundIntensity_E = [0] * len(self.wavelength)
            self.calib_file_name_L = self.spec.model + '_' + 'L_coeff.cal'
            self.calib_file_name_E = self.spec.model + '_' + 'E_coeff.cal'
            if (os.path.exists(self.calib_file_name_L) and os.path.exists(self.calib_file_name_E)):
                # self.calib_file_name_E = [0.5] * len(self.wavelength)
                # need to make sure the file exists
                self.calibCoeff_L = self.read_calib_file(self.calib_file_name_L)
                self.calibCoeff_E = self.read_calib_file(self.calib_file_name_E)
                self.applyCalibL = True
                self.applyCalibE = True
            else:
                # need to put an array of constant here
                self.calibCoeff_L = np.ones(np.shape(self.spec.wavelengths))
                self.calibCoeff_E = np.ones(np.shape(self.spec.wavelengths))
            self.calib_coeff_file_name_E = self.spec.model + '_calibration_coefficients.csv'
            self.calib_coeff_file_name_L = self.calib_coeff_file_name_E
        
            if (os.path.exists(self.calib_coeff_file_name_L)):
                a, b = self.read_calib_coeff_file(self.calib_coeff_file_name_L)
                self.calibCoeff_L = self.calc_calib_coeff(self.wavelength, a, b, self.int_time_L)
                self.calibCoeff_E = self.calc_calib_coeff(self.wavelength, a, b, self.int_time_E)
                self.a_L = a
                self.a_E = a
                self.b_L = b 
                self.b_E = b 
            # self.calibCoeff_E = self.calibCoeff_L
            self.isStopped = True
            self.saveData = False
            self.save_counter = 1
            # spectra dark correction
            self.correct_dark_counts = True
            self.correct_nonlinearity = False
            # plot range
            self.ui.doubleSpinBox_13.setMaximum(int(max(self.wavelength)))
            self.ui.doubleSpinBox_13.setMinimum(int(min(self.wavelength)))
            self.ui.doubleSpinBox_13.setValue(750)
            self.plotRangeLeft = 750
            self.ui.doubleSpinBox_14.setMaximum(int(max(self.wavelength)))
            self.ui.doubleSpinBox_14.setMinimum(int(min(self.wavelength)))
            self.ui.doubleSpinBox_14.setValue(780)
            self.plotRangeRight = 780
            
            self.ui.pushButton_6.setEnabled(True)
            self.ui.pushButton_5.setEnabled(True)
            self.ui.pushButton_18.setEnabled(True)
            self.ui.pushButton_19.setEnabled(True)
            self.ui.pushButton_17.setEnabled(True)
            self.ui.pushButton_20.setEnabled(True)
            # self.ui.pushButton_22.setEnabled(True)
            # self.ui.pushButton_20.setEnabled(True)           
            ########## results calculation #########
            # In @ 687
            if self.spec.model == 'HR2000':
                IN687MIN = 686.8
                IN687MAX = 687.4
                OUTRIGHT687MIN = 690
                OUTRIGHT687MAX = 691
                OUTLEFT687MIN = 684.5
                OUTLEFT687MAX = 686.5
                IN760MIN = 760.2
                IN760MAX = 760.8
                OUTRIGHT760MIN = 770
                OUTRIGHT760MAX = 771
                OUTLEFT760MIN = 756
                OUTLEFT760MAX = 757
            elif self.spec.model == 'QE-PRO':
                IN687MIN = 685.5
                IN687MAX = 687.5
                OUTRIGHT760MIN = 771
                OUTRIGHT760MAX = 773
                OUTLEFT760MIN = 755
                OUTLEFT760MAX = 756
                IN760MIN = 760
                IN760MAX = 762
                OUTLEFT687MIN = 683
                OUTLEFT687MAX = 685
                OUTRIGHT687MIN = 690
                OUTRIGHT687MAX = 691
            else:
                IN687MIN = 686.8
                IN687MAX = 687.4
                OUTRIGHT687MIN = 690
                OUTRIGHT687MAX = 691
                OUTLEFT687MIN = 684.5
                OUTLEFT687MAX = 686.5
                IN760MIN = 760.2
                IN760MAX = 760.8
                OUTRIGHT760MIN = 770
                OUTRIGHT760MAX = 771
                OUTLEFT760MIN = 756
                OUTLEFT760MAX = 757

            self.doubleSpinBox_3.setMinimum(min(self.wavelength))
            self.doubleSpinBox_3.setMaximum(max(self.wavelength))
            self.doubleSpinBox_3.setValue(IN687MIN)

            self.doubleSpinBox_4.setMinimum(min(self.wavelength))
            self.doubleSpinBox_4.setMaximum(max(self.wavelength))
            self.doubleSpinBox_4.setValue(IN687MAX)
            self.setInRange1()
            # In @ 760
            self.doubleSpinBox.setMinimum(min(self.wavelength))
            self.doubleSpinBox.setMaximum(max(self.wavelength))
            self.doubleSpinBox.setValue(IN760MIN)

            self.doubleSpinBox_2.setMinimum(min(self.wavelength))
            self.doubleSpinBox_2.setMaximum(max(self.wavelength))
            self.doubleSpinBox_2.setValue(IN760MAX)
            self.setInRange2()
            # Out left @ 680
            self.doubleSpinBox_5.setMinimum(min(self.wavelength))
            self.doubleSpinBox_5.setMaximum(max(self.wavelength))
            self.doubleSpinBox_5.setValue(OUTLEFT687MIN)

            self.doubleSpinBox_6.setMinimum(min(self.wavelength))
            self.doubleSpinBox_6.setMaximum(max(self.wavelength))
            self.doubleSpinBox_6.setValue(OUTLEFT687MAX)
            self.setOutLeftRange1()
            # Out left @ 760
            self.doubleSpinBox_7.setMinimum(min(self.wavelength))
            self.doubleSpinBox_7.setMaximum(max(self.wavelength))
            self.doubleSpinBox_7.setValue(OUTLEFT760MIN)

            self.doubleSpinBox_8.setMinimum(min(self.wavelength))
            self.doubleSpinBox_8.setMaximum(max(self.wavelength))
            self.doubleSpinBox_8.setValue(OUTLEFT760MAX)
            self.setOutLeftRange2()
            # Out right @ 687
            self.doubleSpinBox_9.setMinimum(min(self.wavelength))
            self.doubleSpinBox_9.setMaximum(max(self.wavelength))
            self.doubleSpinBox_9.setValue(OUTRIGHT687MIN)

            self.doubleSpinBox_10.setMinimum(min(self.wavelength))
            self.doubleSpinBox_10.setMaximum(max(self.wavelength))
            self.doubleSpinBox_10.setValue(OUTRIGHT687MAX)
            self.setOutRightRange1()
            # Out right @ 760
            self.doubleSpinBox_11.setMinimum(min(self.wavelength))
            self.doubleSpinBox_11.setMaximum(max(self.wavelength))
            self.doubleSpinBox_11.setValue(OUTRIGHT760MIN)
        
            self.doubleSpinBox_12.setMinimum(min(self.wavelength))
            self.doubleSpinBox_12.setMaximum(max(self.wavelength))
            self.doubleSpinBox_12.setValue(OUTRIGHT760MAX)
            self.setOutRightRange2()
            self.if_range_changed = False
            time.sleep(2)
            print("Start Worker")
            self.startWorker()
            # self.startControlFoS()
            return self.spec
        else:
            self.lineEdit_2.setText("Spectrometer is disconnecting")
            # sb.closeSpectrometer(self.spec)
            self.spec.close()
            for x in range(1,5):
                time.sleep(0.5)
                # self.progressBar.setValue(x/4*100)
            self.SpectrometerIndicator.value = False #Closes the spectrometer
            self.lineEdit_2.setText("Spectrometer has been disconnected")
            self.pushButton_11.setStyleSheet("QPushButton {background-color: rgb(227,119,100)}")
    def setMeasNum2(self):
        # prev_buffer_size = self.intensity_buffersize
        # curr_buffer_size = self.ui.spinBox_3.value()
        self.intensity_buffersize = self.ui.spinBox_3.value()
        if self.comboBox.currentIndex() == 0:
            self.ui.lineEdit_5.setText("Number of Meas: " + str(self.intensity_buffersize) + " (L), " + str(self.intensity_buffersize) + " (E).")
        elif self.comboBox.currentIndex() == 1:
            self.ui.lineEdit_5.setText("Current fibre channel: L. Number of Meas: " + str(self.intensity_buffersize))
        else:
            self.ui.lineEdit_5.setText("Current fibre channel: E. Number of Mease: " + str(self.intensity_buffersize))
        self.ui.lineEdit_5.setEnabled(False)


        # if prev_buffer_size > curr_buffer_size:
        #     for i in range(0, (prev_buffer_size - curr_buffer_size)):
        #         self.intensity_L_queue.pop(0)
        # else:
        #     for i in range(0, (curr_buffer_size - prev_buffer_size)):
        #         self.intensity_L_queue.append([0] * len(self.wavelength))
        #     self.intensity_buffersize = curr_buffer_size
    # def setMeasNum(self):
    #     if self.if_L:
    #         prev_buffer_size = self.intensity_buffersize
    #         curr_buffer_size = self.ui.spinBox_3.value()
    #         if prev_buffer_size > curr_buffer_size:
    #             for i in range(0, (prev_buffer_size - curr_buffer_size)):
    #                 self.intensity_L_queue.pop(0)
    #         else:
    #             for i in range(0, (curr_buffer_size - prev_buffer_size)):
    #                 self.intensity_L_queue.append([0] * len(self.wavelength))
    #         self.intensity_buffersize = curr_buffer_size
    #     else:
    #         prev_buffer_size = self.intensity_buffersize
    #         curr_buffer_size = self.ui.spinBox_3.value()
    #         if prev_buffer_size > curr_buffer_size:
    #             for i in range(0, (prev_buffer_size - curr_buffer_size)):
    #                 self.intensity_E_queue.pop(0)
    #                 self.intensity_E_time_queue.pop(0)
    #         else:
    #             for i in range(0, (curr_buffer_size - prev_buffer_size)):
    #                 self.intensity_E_queue.append([0] * len(self.wavelength))
    #                 self.intensity_E_time_queue.append("") 
    #         self.intensity_buffersize = curr_buffer_size
    #     self.ui.lineEdit_5.setText("Number of Meas: " + str(self.intensity_buffersize) + " (L), " + str(self.intensity_buffersize) + " (E).")
     
    def setSpecIntTime(self):
        self.isIntTimeChanged = True
        
        self.int_time_L = self.ui.spinBox.value() * 1000
        if self.int_time_L < self.spec.integration_time_micros_limits[0] | self.int_time_L > self.spec.integration_time_micros_limits[1]:
            print('Integration time is too short or too long')
        
        self.int_time_E = self.ui.spinBox_4.value() * 1000
        if self.int_time_E < self.spec.integration_time_micros_limits[0] | self.int_time_E > self.spec.integration_time_micros_limits[1]:
            print('Integration time is too short or too long')
        
        #for x in range(1,4):
            #time.sleep(0.5)
            #self.progressBar.setValue(x/3*100)
        # sb.setIntegrationTime(time)
        if self.if_L:
            if self.a_L is not None and self.b_L is not None:
                self.calibCoeff_L = self.calc_calib_coeff(self.wavelength, self.a_L, self.b_L, self.int_time_L)
        else:
            if self.a_E is not None and self.b_E is not None:
                self.calibCoeff_E = self.calc_calib_coeff(self.wavelength, self.a_E, self.b_E, self.int_time_E)
        # self.spec.integration_time_micros(time)
        if self.if_L:
            self.ui.lineEdit_2.setText("Integration time (L) has been set to "+ str(self.ui.spinBox.value()) + " ms")
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
        else:
            self.ui.lineEdit_2.setText("Integration time (E) has been set to "+ str(self.ui.spinBox_4.value()) + " ms")
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
        if self.if_L:
            self.updateRate = self.int_time_L/1000 * self.scans_to_avg_L
        else:
            self.updateRate = self.int_time_E/1000 * self.scans_to_avg_E
        # self.timer.setInterval(int(self.updateRate))
    def setScansToAvg(self):
        if self.if_L:
            self.scans_to_avg_L = self.ui.spinBox_2.value()
            self.current_scans_to_avg = self.scans_to_avg_L
            self.updateRate = self.int_time_L/1000 * self.scans_to_avg_L
            self.ui.lineEdit_2.setText("Scans to average (L) has been set to "+ str(self.scans_to_avg_L))
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
        else:
            self.scans_to_avg_E = self.ui.spinBox_5.value()
            self.current_scans_to_avg = self.scans_to_avg_E
            self.updateRate = self.int_time_E/1000 * self.scans_to_avg_E
            self.ui.lineEdit_2.setText("Scans to average (E) has been set to "+ str(self.scans_to_avg_E))
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
        # self.timer.setInterval(int(self.updateRate))
        # scans = self.scansToAvg.value()
        # self.scans_to_avg = scans
        # self.lineEdit_2.setText("Scans to average has been set to "+ str(scans))
        
       
        # print(scans)
    def setFibreMode(self):
        currentIndex = self.ui.comboBox.currentIndex()
        if currentIndex == 0:
            self.BothFibreMode()
            self.ui.lineEdit_5.setText("Number of Meas: " + str(self.intensity_buffersize) + " (L), " + str(self.intensity_buffersize) + " (E).")
        elif currentIndex == 1:
            self.LOnlyFibreMode()
            self.ui.lineEdit_5.setText("Current fibre channel: L. Number of Meas: " + str(self.intensity_buffersize))
        else:
            self.EOnlyFibreMode()
            self.ui.lineEdit_5.setText("Current fibre channel: E. Number of Meas: " + str(self.intensity_buffersize))
            
    def EOnlyFibreMode(self):
        # if self.ui.checkBox.isChecked():
        self.ui.checkBox_2.setEnabled(False)
        self.ui.lineEdit_4.setText("Current channel: Irradiance (E).")
        self.ui.lineEdit_4.setEnabled(False)
        self.ui.pushButton_12.setEnabled(False)
        self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_9.setEnabled(True)
        self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_14.setEnabled(False)
        self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_13.setEnabled(True)
        self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.if_L = False
        self.if_E = True

        if self.SpectrometerIndicator.value == True:
            self.setSpecIntTime()
            self.setScansToAvg()
        # self.serialcomm.write("off".encode())
        # else:
        #     self.ui.checkBox_4.setEnabled(True)
        #     self.ui.checkBox_3.setEnabled(True)
        #     self.ui.pushButton_12.setEnabled(False)
        #     self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_9.setEnabled(False)
        #     self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_14.setEnabled(False)
        #     self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_13.setEnabled(False)
        #     self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
    def LOnlyFibreMode(self):
        # if self.ui.checkBox_3.isChecked():
        self.ui.checkBox_2.setEnabled(False)
        self.ui.lineEdit_4.setText("Current channel: Radiance (L).")
        self.ui.lineEdit_4.setEnabled(False)
        # self.ui.checkBox.setEnabled(False)
        # self.ui.checkBox_4.setEnabled(False)
        self.ui.pushButton_12.setEnabled(True)
        self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_9.setEnabled(False)
        self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_14.setEnabled(True)
        self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_13.setEnabled(False)
        self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.if_L = True
        self.if_E = False
        if self.SpectrometerIndicator.value == True:
            self.setSpecIntTime()
            self.setScansToAvg()
        # self.serialcomm.write("on".encode())
        # else:
        #     self.ui.checkBox.setEnabled(True)
        #     self.ui.checkBox_4.setEnabled(True)
        #     self.ui.pushButton_12.setEnabled(False)
        #     self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_9.setEnabled(False)
        #     self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_14.setEnabled(False)
        #     self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_13.setEnabled(False)
        #     self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
    def BothFibreMode(self):
        # if self.ui.checkBox_4.isChecked():
        self.ui.checkBox_2.setEnabled(True)
        # self.ui.checkBox.setEnabled(False)
        # self.ui.checkBox_3.setEnabled(False)
        self.ui.pushButton_12.setEnabled(True)
        self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_9.setEnabled(True)
        self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_14.setEnabled(True)
        self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        self.ui.pushButton_13.setEnabled(True)
        self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        if self.ui.checkBox_2.isChecked():
            # i = 'off'
            self.if_L = False
        else:
            # i = 'on'
            self.if_L = True
        # else:
        #     self.ui.checkBox.setEnabled(True)
        #     self.ui.checkBox_3.setEnabled(True)
        #     self.ui.pushButton_12.setEnabled(False)
        #     self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_9.setEnabled(False)
        #     self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_14.setEnabled(False)
        #     self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        #     self.ui.pushButton_13.setEnabled(False)
        #     self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
    
    def EOnlyFibreMode2(self):
        if self.ui.checkBox.isChecked():
            self.ui.checkBox_2.setEnabled(False)
            self.ui.checkBox_4.setEnabled(False)
            self.ui.checkBox_3.setEnabled(False)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_9.setEnabled(True)
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_13.setEnabled(True)
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.if_L = False
            self.serialcomm.write("off".encode())
        else:
            self.ui.checkBox_4.setEnabled(True)
            self.ui.checkBox_3.setEnabled(True)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_13.setEnabled(False)
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
    def LOnlyFibreMode2(self):
        if self.ui.checkBox_3.isChecked():
            self.ui.checkBox_2.setEnabled(False)
            self.ui.checkBox.setEnabled(False)
            self.ui.checkBox_4.setEnabled(False)
            self.ui.pushButton_12.setEnabled(True)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_14.setEnabled(True)
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_13.setEnabled(False)
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.if_L = True
            self.serialcomm.write("on".encode())
        else:
            self.ui.checkBox.setEnabled(True)
            self.ui.checkBox_4.setEnabled(True)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_13.setEnabled(False)
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
    def BothFibreMode2(self):
        if self.ui.checkBox_4.isChecked():
            self.ui.checkBox_2.setEnabled(True)
            self.ui.checkBox.setEnabled(False)
            self.ui.checkBox_3.setEnabled(False)
            self.ui.pushButton_12.setEnabled(True)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_9.setEnabled(True)
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_14.setEnabled(True)
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_13.setEnabled(True)
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            if self.ui.checkBox_2.isChecked():
                # i = 'off'
                self.if_L = False
            else:
                # i = 'on'
                self.if_L = True
        else:
            self.ui.checkBox.setEnabled(True)
            self.ui.checkBox_3.setEnabled(True)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_13.setEnabled(False)
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
    def trigger_switched(self):
        if self.ui.checkBox_2.isChecked():
            self.if_L = False
            self.if_E = True
            i = 'off'
            self.serialcomm.write(i.encode())
            self.ui.lineEdit_2.setText("Irradiance selected.")
            self.ui.lineEdit_4.setText("Current channel: Irradiance (E).")
            self.ui.lineEdit_4.setEnabled(False)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_9.setEnabled(True)
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_13.setEnabled(True)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            # self.plot_datas[0] = None
            # self.plot_datas[3] = None
            # self.plot_datas[6] = None
            self.reference_plots[6] = None
            self.canvases[6].axes.clear()
            if self.reference_plots[1] is not None:
                self.reference_plots[1].set_alpha(0.4)
                self.canvases[1].draw()
            if self.reference_plots[4] is not None:
                self.reference_plots[4].set_alpha(0.4)
                self.canvases[4].draw()
            if self.reference_plots[7] is not None:
                self.reference_plots[7].set_alpha(0.4)
                self.canvases[7].draw()
            self.spec.integration_time_micros(self.int_time_E)
            self.scans_to_avg_E = self.ui.spinBox_5.value()
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(28,255,0)}")
            self.current_scans_to_avg = self.scans_to_avg_E
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(28,255,0)}")
            # self.plot_datas[7] = None
            # self.reference_plots[7] = None
            # self.canvases[7].axes.clear()
            # self.ui.spinBox.setEnabled(False)
            # self.ui.spinBox_4.setEnabled(True)
            # self.ui.pushButton_12.setEnabled(False)
            # self.ui.pushButton_9.setEnabled(True)
        else:
            self.if_L = True
            self.if_E = False
            i = 'on'
            self.serialcomm.write(i.encode())
            self.ui.lineEdit_2.setText("L Fibre selected.")
            self.ui.lineEdit_4.setText("Current channel: Radiance (L).")
            self.ui.lineEdit_4.setEnabled(False)
            self.ui.pushButton_12.setEnabled(True)
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_14.setEnabled(True)
            self.ui.pushButton_13.setEnabled(False)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
            # self.plot_datas[1] = None
            # self.plot_datas[4] = None
            # self.plot_datas[7] = None
            self.reference_plots[7] = None
            self.canvases[7].axes.clear()
            if self.reference_plots[0] is not None:
                self.reference_plots[0].set_alpha(0.4)
                self.canvases[0].draw()
            if self.reference_plots[3] is not None:
                self.reference_plots[3].set_alpha(0.4)
                self.canvases[3].draw()
            if self.reference_plots[6] is not None:
                self.reference_plots[6].set_alpha(0.4)
                self.canvases[6].draw()
            self.spec.integration_time_micros(self.int_time_L)
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(28,255,0)}")
            self.scans_to_avg_L = self.ui.spinBox_2.value()
            self.current_scans_to_avg = self.scans_to_avg_L
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(28,255,0)}")
        # print(self.if_L)
            # self.ui.spinBox.setEnabled(True)
            # self.ui.spinBox_4.setEnabled(False)
            # self.ui.pushButton_12.setEnabled(True)
            # self.ui.pushButton_9.setEnabled(False)
    def startOptimize(self):
        print('Start optimization')
        # intensity = self.spec.intensities()
        intensity = self.spec.intensities(correct_dark_counts=self.correct_dark_counts, correct_nonlinearity=False)
        # print(intensity)
        if self.if_L:
            int_time = self.int_time_L
            self.ui.spinBox_2.setValue(1)
            # self.setScansToAvg()
        else:
            int_time = self.int_time_E
            self.ui.spinBox_5.setValue(1)
        print("current maximum intensity: " + str(max(intensity)))
        # # if(max(intensity) > self.spec.max_intensity):
        # #     print("NEED OPTIMIZATION")
        # self.graphPlot3.setBackground('k')
        # self.graphPlot3.getAxis('left').setTextPen('w')
        # self.graphPlot3.getAxis('bottom').setTextPen('w')
        # self.graphPlot3.getAxis('left').setPen('w')
        # self.graphPlot3.getAxis('bottom').setPen('w')
        # optimizeStepSize = self.optimizeStepSize.value()
        optimizeStepSize = 1500 # 1.5 ms 
        while (max(intensity) >= self.spec.max_intensity * 0.9 and int_time > self.spec.integration_time_micros_limits[0]):
            int_time = int_time - optimizeStepSize
            self.lineEdit_3.setText('Reducing integration time ' + str(int_time))
            self.spec.integration_time_micros(int_time)
            intensity, dark_temp = self.spec.intensities(correct_dark_counts=self.correct_dark_counts, correct_nonlinearity=False)
            # wavelength = self.spec.wavelengths()
            pg.QtGui.QGuiApplication.processEvents()
            # self.optimizeMessage.setText("Optimization, current integration time: " + str(int_time) + " ms")
            # self.luminescencePlot3 = self.graphPlot3.plot(wavelength[1::], intensity[1::], clear = True, pen = pg.mkPen('g'))
            # labelStyle = {'color': 'k', 'font-size': '10pt'}
            # self.graphPlot3.setLabel('bottom', text = 'Wavelength (nm)')
            # self.graphPlot3.setLabel('left', text = 'Intensity (a.u.)')
            # time.sleep(int_time/1000000)
        if self.if_L:
            self.ui.spinBox.setValue(int(int_time/1000))
            self.setSpecIntTime()
            self.lineEdit_3.setText("The optimized integration time (L) is set to " + str(int_time/1000) + ' ms')
            # self.ui.spinBox_2.setValue(self.scans_to_avg_L)
            self.ui.pushButton_5.setStyleSheet("QPushButton {background-color: rgb(85,255,0)}")
            # self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
        else:
            self.ui.spinBox_4.setValue(int(int_time/1000))
            self.setSpecIntTime()
            self.lineEdit_3.setText("The optimized integration time (E) is set to " + str(int_time/1000) + ' ms')
            # self.ui.spinBox_5.setValue(self.scans_to_avg_E)
            self.ui.pushButton_5.setStyleSheet("QPushButton {background-color: rgb(85,255,0)}")
        # self.stopWorker()
            # self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
    def newDirectory(self):
        self.directoryPath = QFileDialog.getExistingDirectory(self,"Choose a Directory to Save the data")
        self.ui.lineEdit.setText(self.directoryPath)
        return self.directoryPath
    def disableSave(self):
        self.ui.pushButton_19.setEnabled(False)
        self.ui.pushButton_17.setEnabled(False)
        # self.ui.pushButton_20.setEnabled(False)
    def enableSave(self):
        self.ui.pushButton_20.setEnabled(True)
        self.ui.pushButton_19.setEnabled(True)
        self.ui.pushButton_17.setEnabled(True)
    def getSpectra(self, correct_dark_counts, correct_nonlinearity):
        scans = self.current_scans_to_avg
        # t = self.integrationTime.value()
        x = self.wavelength
        spectrum_final = [0] * len(x)
        dark_mean = 0
        for iterator in range(1,scans+1):
            if self.isStopped:
                break
            # self.busySignal.emit()
            inten_temp,dark_temp  = self.spec.intensities(correct_dark_counts=correct_dark_counts, correct_nonlinearity=correct_nonlinearity)
            # dark_len, dark_temp = self.spec.darkPixels()
            dark_mean = dark_mean + dark_temp
            # print(len(dark_spec_temp))
            spectrum_final = spectrum_final + inten_temp
            print('Measuring ' + str(iterator))
            if self.if_L:
                if self.int_time_L * self.current_scans_to_avg > 1000000:
                    self.ui.lineEdit_2.setText('Measuring Scan No. ' + ' ' + str(iterator))
            else:
                if self.int_time_E * self.current_scans_to_avg > 1000000:
                    self.ui.lineEdit_2.setText('Measuring Scan No. ' + ' ' + str(iterator))
            
            
            
        # spectrum_final = spectrum_final/scans
        # print(spectrum_final)
        spectrum_final = [s / scans for s in spectrum_final]
        dark_mean = dark_mean/scans
        # dark_final = [d / scans for d in dark_final]
        return spectrum_final, dark_mean
        
    def measureBackground(self):
        # if self.if_L:
        #     print("inte time: " + str(self.int_time_L))
        #     self.spec.integration_time_micros(int(self.ui.spinBox.value() * 1000))
        # else:
        #     print("inte time: " + str(self.int_time_E))
        #     self.spec.integration_time_micros(int(self.ui.spinBox_4.value() * 1000))
        # wavelength = self.spec.wavelengths()
        # self.backgroundIntensity = self.getSpectra(correct_dark_counts=True, correct_nonlinearity=False)
        # self.backgroundIntensity = self.intensity - self.dark_mean
        self.backgroundIntensity = self.intensity
        # if self.if_L:
        #     self.backgroundIntensity_L = backgroundIntensity
        # else:
        #     self.backgroundIntensity_E = backgroundIntensity
        QtWidgets.QApplication.processEvents()
        self.ui.lineEdit_3.setText("Background Spectrum measured")
        # labelStyle = {'color': 'k', 'font-size': '10pt'}
        self.canvases[2].axes.set_xlabel('Wavelength (nm)')
        self.canvases[2].axes.set_ylabel('Intensity ')
        self.canvases[2].axes.set_title("Dark", color='w')
        [t.set_color('w') for t in self.canvases[2].axes.xaxis.get_ticklabels()]
        [t.set_color('w') for t in self.canvases[2].axes.yaxis.get_ticklabels()]
        if self.reference_plots[2] is None:
            plot_refs = self.canvases[2].axes.plot(self.wavelength[1::], self.backgroundIntensity[1::], color=(1,0,0.29))
            self.reference_plots[2] = plot_refs[0]	
        else:
            self.reference_plots[2].set_ydata(self.backgroundIntensity[1::])
                    
        self.canvases[2].draw()
        # self.graphPlot3.setLabel('left', text = 'Intensity (a.u.)')
        
    def plotSpectra(self):
        try:
            print('ACTIVE THREADS:',self.threadpool.activeThreadCount(),end=" \r")
            while self.isStopped is False:
                QtWidgets.QApplication.processEvents()
                try:
                    self.ydata = self.q.get_nowait()
                except queue.Empty:
                    break
                # print(max(self.ydata))
                self.xdata = self.wavelength
                # self.ydata = self.intensity
                
                if self.if_L:
                    max_y = max(self.ydata[1::])
                    min_y = min(self.ydata[1::])
                    
                    self.canvases[1].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[1].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[1].axes.set_ylabel('Intensity ')
                    self.canvases[1].axes.set_title("Raw L", color='w')
                    [t.set_color('w') for t in self.canvases[1].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[1].axes.yaxis.get_ticklabels()]
                    self.plot_datas[1] = self.ydata[1::]
                    if self.reference_plots[1] is None:
                        plot_refs = self.canvases[1].axes.plot(self.xdata[1::],self.ydata[1::], color=(0,1,0.29), alpha = 1)
                        self.reference_plots[1] = plot_refs[0]	
                    else:
                        self.reference_plots[1].set_ydata(self.ydata[1::])
                        self.reference_plots[1].set_alpha(1)
                    self.canvases[1].draw()

                    # self.ydata_calib = [a * b for a,b in zip (self.ydata, self.calib_file_name_L)]
                    self.ydata_calib = np.multiply(self.ydata, self.calibCoeff_L)
                    min_y = min(self.ydata_calib[min(self.wminmax):max(self.wminmax)])
                    max_y = max(self.ydata_calib[min(self.wminmax):max(self.wminmax)])
                    self.canvases[4].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[4].axes.set_xlim(xmin = self.wavelength[min(self.wminmax)], xmax = self.wavelength[max(self.wminmax)])
                    self.canvases[4].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[4].axes.set_ylabel('Intensity ')
                    self.canvases[4].axes.set_title("Calib L",color='w')
                    [t.set_color('w') for t in self.canvases[4].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[4].axes.yaxis.get_ticklabels()]
                    self.plot_datas[4] = self.ydata_calib
                    if self.reference_plots[4] is None:
                        plot_refs = self.canvases[4].axes.plot(self.xdata[1::],self.ydata_calib[1::], color=(0,1,0.29), alpha = 1)
                        self.reference_plots[4] = plot_refs[0]	
                    else:
                        self.reference_plots[4].set_ydata(self.ydata_calib[1::])
                        self.reference_plots[4].set_alpha(1)
                    self.canvases[4].draw()
                    wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
                    # print(self.wavelength[min(wAB)])
                    # print(self.wavelength[max(wAB)])
                    min_y = min(self.ydata_calib[min(wAB):max(wAB)])
                    max_y = max(self.ydata_calib[min(wAB):max(wAB)])
                    # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
                    self.canvases[7].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[7].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax=self.wavelength[max(wAB)])
                    self.canvases[7].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[7].axes.set_ylabel('Intensity ')
                    self.canvases[7].axes.set_title("Calib L (A-B)",color='w')
                    [t.set_color('w') for t in self.canvases[7].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[7].axes.yaxis.get_ticklabels()]
                    self.plot_datas[7] = self.ydata_calib
                    if self.reference_plots[7] is None:
                        # plot_refs = self.canvases[7].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29))
                        plot_refs = self.canvases[7].axes.plot(self.wavelength, self.ydata_calib, color=(0,1,0.29), alpha = 1)
                        self.reference_plots[7] = plot_refs[0]	
                    else:
                        self.reference_plots[7].set_ydata(self.ydata_calib)
                        self.reference_plots[7].set_alpha(1)
                    self.canvases[7].draw()
                    self.Lin_687 = self.getResultsMin(self.plot_datas[4], self.InRange1Min, self.InRange1Max)
                    self.Lin_760 = self.getResultsMin(self.plot_datas[4], self.InRange2Min, self.InRange2Max)
                    self.Lout_left_687 = self.getResultsMax(self.plot_datas[4], self.OutLeftRange1Min, self.OutLeftRange1Max)
                    self.Lout_left_760 = self.getResultsMax(self.plot_datas[4], self.OutLeftRange2Min, self.OutLeftRange2Max)
                    self.Lout_right_687 = self.getResultsMax(self.plot_datas[4], self.OutRightRange1Min, self.OutRightRange1Max)
                    self.Lout_right_760 = self.getResultsMax(self.plot_datas[4], self.OutRightRange2Min, self.OutRightRange2Max)
                    # self.lineEdit_4.setText("@" + str(round(self.Lin[0],3)) + " (nm): " + str(round(self.Lin[1],2)))
                    # self.lineEdit_5.setText("@" + str(round(self.Lout_left[0],3)) + " (nm): " + str(round(self.Lout_left[1],2)))
                    # self.lineEdit_6.setText("@" + str(round(self.Lout_right[0],3)) + " (nm): " + str(round(self.Lout_right[1],2)))
                    # self.Lout_avg = np.mean([self.Lout_left[1], self.Lout_right[1]])
                    # self.lineEdit_10.setText(str(round(self.Lout_avg,2)))
                    if self.intensity_E is not None:
                        # print("E fibre has data")
                        self.ui.lineEdit_2.setText("E fibre has data")
                        self.reflectance = self.getReflectance2(self.plot_datas[3], self.plot_datas[4])
                        # self.reflectance = self.getReflectance( self.intensity_E, self.ydata)
                        # min_y = np.divide(np.max(self.ydata_calib),np.min(np.multiply(np.subtract(self.intensity_E[1::], self.backgroundIntensity[1::]), self.calibCoeff_E[1::])))
                        # max_y = np.nanmax(self.reflectance[1::])
                        # min_y = np.nanmin(self.reflectance[self.reflectance != np.NINF])
                        max_y = 1.2
                        min_y = 0
                        # max_y = np.divide(np.max(self.ydata_calib),np.max(np.multiply(np.subtract(self.intensity_E[1::], self.backgroundIntensity[1::]), self.calibCoeff_E[1::])))
                        # print(min_y)
                        # print(max_y)
                        self.canvases[5].axes.set_ylim(ymin = min_y, ymax= max_y )
                        self.canvases[5].axes.set_xlim(xmin = self.wavelength[min(self.wminmax)], xmax =self.wavelength[max(self.wminmax)])
                        self.canvases[5].axes.set_xlabel('Wavelength (nm)')
                        self.canvases[5].axes.set_ylabel('Intensity ')
                        self.canvases[5].axes.set_title("Reflectance",color='w')
                        [t.set_color('w') for t in self.canvases[5].axes.xaxis.get_ticklabels()]
                        [t.set_color('w') for t in self.canvases[5].axes.yaxis.get_ticklabels()]
                        self.plot_datas[5] = self.reflectance[1::]
                        if self.reference_plots[5] is None:
                            plot_refs = self.canvases[5].axes.plot(self.wavelength[1::],self.reflectance[1::], color=(0,1,0.29))
                            self.reference_plots[5] = plot_refs[0]	
                        else:
                            self.reference_plots[5].set_ydata(self.reflectance[1::])
                        self.canvases[5].draw()
                        # min_y = min(self.reflectance[min(wAB):max(wAB)])
                        # max_y = max(self.reflectance[min(wAB):max(wAB)])
                        # self.ui.lineEdit_2.setText("Measurement On " + str(max_y) + " " + str(min_y))
                        self.canvases[8].axes.set_ylim(ymin = min_y, ymax= max_y )
                        self.canvases[8].axes.set_xlabel('Wavelength (nm)')
                        self.canvases[8].axes.set_ylabel('Intensity ')
                        self.canvases[8].axes.set_title("Reflectance (A-B)",color='w')
                        [t.set_color('w') for t in self.canvases[8].axes.xaxis.get_ticklabels()]
                        [t.set_color('w') for t in self.canvases[8].axes.yaxis.get_ticklabels()]
                        self.plot_datas[8] = self.reflectance[min(wAB):max(wAB)]
                        if self.reference_plots[8] is None:
                            plot_refs = self.canvases[8].axes.plot(self.wavelength[min(wAB):max(wAB)],self.reflectance[min(wAB):max(wAB)], color=(0,1,0.29))
                            self.reference_plots[8] = plot_refs[0]	
                        else:
                            self.reference_plots[8].set_ydata(self.reflectance[min(wAB):max(wAB)])
                        self.canvases[8].draw()
                        self.Ein_687 = self.getResultsMin(self.plot_datas[3], self.InRange1Min, self.InRange1Max)
                        self.Ein_760 = self.getResultsMin(self.plot_datas[3], self.InRange2Min, self.InRange2Max)
                        self.Eout_left_687 = self.getResultsMax(self.plot_datas[3], self.OutLeftRange1Min, self.OutLeftRange1Max)
                        self.Eout_right_687 = self.getResultsMax(self.plot_datas[3], self.OutRightRange1Min, self.OutRightRange1Max)
                        self.Eout_left_760 = self.getResultsMax(self.plot_datas[3], self.OutLeftRange2Min, self.OutLeftRange2Max)
                        self.Eout_right_760 = self.getResultsMax(self.plot_datas[3], self.OutRightRange2Min, self.OutRightRange2Max)
                        wL687 = (self.Eout_right_687[0] - self.Ein_687[0])/(self.Eout_right_687[0] - self.Eout_left_687[0])
                        wL760 = (self.Eout_right_760[0] - self.Ein_760[0])/(self.Eout_right_760[0] - self.Eout_left_760[0])
                        wR687 = (self.Ein_687[0] - self.Eout_left_687[0])/(self.Eout_right_687[0] - self.Eout_left_687[0])
                        wR760 = (self.Ein_760[0] - self.Eout_left_760[0])/(self.Eout_right_760[0] - self.Eout_left_760[0])
                        
                        FLD1 = (((wL687 * self.Eout_left_687[1] + wR687 * self.Eout_right_687[1]) * self.Lin_687[1])-(self.Ein_687[1]*(wL687 * self.Lout_left_687[1] + wR687 * self.Lout_right_687[1])))/((wL687 * self.Eout_left_687[1] + wR687 * self.Eout_right_687[1])-self.Ein_687[1])
                        FLD2 = (((wL760 * self.Eout_left_760[1] + wR760 * self.Eout_right_760[1]) * self.Lin_760[1])-(self.Ein_760[1]*(wL760 * self.Lout_left_760[1] + wR760 * self.Lout_right_760[1])))/((wL760 * self.Eout_left_760[1] + wR760 * self.Eout_right_760[1])-self.Ein_760[1])
                        
                        # FLD2 = ((np.mean([self.Eout_left_760[1], self.Eout_right_760[1]]) * self.Lin_760[1])-(self.Ein_760[1]*np.mean([self.Lout_left_760[1], self.Lout_right_760[1]])))/(np.mean([self.Eout_left_760[1], self.Eout_right_760[1]])-self.Ein_760[1])
                        
                        self.ui.lineEdit_13.setText(str(round(FLD1,3)))
                        self.ui.lineEdit_15.setText(str(round(FLD2,3)))

                        if self.if_range_changed:
                            # print(self.if_range_changed)
                            # Edata_calib = np.multiply(np.subtract(self.intensity_E, self.backgroundIntensity), self.calibCoeff_E)
                            y_data = self.plot_datas[3]
                            min_y = min(y_data[min(wAB):max(wAB)])
                            max_y = max(y_data[min(wAB):max(wAB)])
                            # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
                            self.canvases[6].axes.set_ylim(ymin = min_y, ymax= max_y)
                            self.canvases[6].axes.set_xlabel('Wavelength (nm)')
                            self.canvases[6].axes.set_ylabel('Intensity ')
                            self.canvases[6].axes.set_title("Calib E (A-B)",color='w')
                            [t.set_color('w') for t in self.canvases[6].axes.xaxis.get_ticklabels()]
                            [t.set_color('w') for t in self.canvases[6].axes.yaxis.get_ticklabels()]
                            
                            self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)], y_data[min(wAB):max(wAB)],color=(0,1,0.29), alpha = 0.4)
                                # print(self.reference_plots[6].get_ydata())
                            self.canvases[6].draw()
                            self.if_range_changed = False
                else:
                    max_y = max(self.ydata[1::])
                    min_y = min(self.ydata[1::])
                    
                    self.canvases[0].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[0].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[0].axes.set_ylabel('Intensity ')
                    self.canvases[0].axes.set_title("Raw E", color='w')
                    [t.set_color('w') for t in self.canvases[0].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[0].axes.yaxis.get_ticklabels()]
                    self.plot_datas[0] = self.ydata[1::]
                    if self.reference_plots[0] is None:
                        plot_refs = self.canvases[0].axes.plot(self.xdata[1::],self.ydata[1::], color=(0,1,0.29), alpha = 1)
                        self.reference_plots[0] = plot_refs[0]	
                    else:
                        self.reference_plots[0].set_ydata(self.ydata[1::])
                        self.reference_plots[0].set_alpha(1)
                    self.canvases[0].draw()
                    # self.ydata_calib = [a * b for a,b in zip (self.ydata, self.calib_file_name_L)]
                    self.ydata_calib = np.multiply(self.ydata, self.calibCoeff_E)
                    

                    min_y = min(self.ydata_calib[min(self.wminmax):max(self.wminmax)])
                    max_y = max(self.ydata_calib[min(self.wminmax):max(self.wminmax)])
                    self.canvases[3].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[3].axes.set_xlim(xmin = self.wavelength[min(self.wminmax)], xmax = self.wavelength[max(self.wminmax)])
                    self.canvases[3].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[3].axes.set_ylabel('Intensity ')
                    self.canvases[3].axes.set_title("Calib E",color='w')
                    [t.set_color('w') for t in self.canvases[3].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[3].axes.yaxis.get_ticklabels()]
                    self.plot_datas[3] = self.ydata_calib
                    if self.reference_plots[3] is None:
                        plot_refs = self.canvases[3].axes.plot(self.xdata,self.ydata_calib, color=(0,1,0.29), alpha = 1)
                        self.reference_plots[3] = plot_refs[0]	
                    else:
                        self.reference_plots[3].set_ydata(self.ydata_calib)
                        self.reference_plots[3].set_alpha(1)
                    self.canvases[3].draw()
                    wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
                    # print(self.wavelength[min(wAB)])
                    # print(self.wavelength[max(wAB)])
                    min_y = min(self.ydata_calib[min(wAB):max(wAB)])
                    max_y = max(self.ydata_calib[min(wAB):max(wAB)])
                    # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
                    self.canvases[6].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[6].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[6].axes.set_ylabel('Intensity ')
                    self.canvases[6].axes.set_title("Calib E (A-B)",color='w')
                    [t.set_color('w') for t in self.canvases[6].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[6].axes.yaxis.get_ticklabels()]
                    self.plot_datas[6] = self.ydata_calib[min(wAB):max(wAB)]
                    if self.reference_plots[6] is None:
                        plot_refs = self.canvases[6].axes.plot(self.wavelength[min(wAB):max(wAB)],self.ydata_calib[min(wAB):max(wAB)], color=(0,1,0.29), alpha = 1)
                        self.reference_plots[6] = plot_refs[0]	
                    else:
                        self.reference_plots[6].set_ydata(self.ydata_calib[min(wAB):max(wAB)])
                        self.reference_plots[6].set_alpha(1)
                    self.canvases[6].draw()
                    self.Ein_687 = self.getResultsMin(self.plot_datas[3], self.InRange1Min, self.InRange1Max)
                    self.Ein_760 = self.getResultsMin(self.plot_datas[3], self.InRange2Min, self.InRange2Max)
                    self.Eout_left_687 = self.getResultsMax(self.plot_datas[3], self.OutLeftRange1Min, self.OutLeftRange1Max)
                    self.Eout_right_687 = self.getResultsMax(self.plot_datas[3], self.OutRightRange1Min, self.OutRightRange1Max)
                    self.Eout_left_760 = self.getResultsMax(self.plot_datas[3], self.OutLeftRange2Min, self.OutLeftRange2Max)
                    self.Eout_right_760 = self.getResultsMax(self.plot_datas[3], self.OutRightRange2Min, self.OutRightRange2Max)
                    # self.lineEdit_7.setText("@" + str(round(self.Ein[0],3)) + " (nm): " + str(round(self.Ein[1],2)))
                    # self.lineEdit_8.setText("@" + str(round(self.Eout_left[0],3)) + " (nm): " + str(round(self.Eout_left[1],2)))
                    # self.lineEdit_9.setText("@" + str(round(self.Eout_right[0],3)) + " (nm): " + str(round(self.Eout_right[1],2)))
                    # self.Eout_avg = np.mean([self.Eout_left[1], self.Eout_right[1]])
                    # self.lineEdit_11.setText(str(round(self.Eout_avg,2)))
                    
                    if self.intensity_L is not None:
                        self.ui.lineEdit_2.setText("L fibre has data")
                        self.reflectance = self.getReflectance2(self.plot_datas[3], self.plot_datas[4])
                        # self.reflectance = self.getReflectance(self.ydata, self.intensity_L)
                        # min_y = np.divide(np.min(np.multiply(np.subtract(self.intensity_L[1::], self.backgroundIntensity[1::]), self.calibCoeff_L[1::])),np.max(self.ydata_calib[1::]))
                        # max_y = np.divide(np.max(np.multiply(np.subtract(self.intensity_L[1::], self.backgroundIntensity[1::]), self.calibCoeff_L[1::])),np.min(self.ydata_calib[1::]))
                        # max_y = np.nanmax(self.reflectance[1::])
                        # min_y = np.nanmin(self.reflectance[self.reflectance != np.NINF])
                        # max_y = np.nanmax(self.reflectance[self.reflectance != np.Inf])
                        # print("Reflectance max: " + str(max_y))
                        # min_y = np.nanmin(self.reflectance[self.reflectance != np.NINF and self.reflectance != np.Inf])
                        # print("Reflectance min: " + str(np.nanmin(self.reflectance[self.reflectance != np.NINF])))
                        min_y = 0
                        max_y = 1.2
                        self.canvases[5].axes.set_ylim(ymin = min_y , ymax= max_y )
                        self.canvases[5].axes.set_xlim(xmin = self.wavelength[min(self.wminmax)], xmax = self.wavelength[max(self.wminmax)])
                        self.canvases[5].axes.set_xlabel('Wavelength (nm)')
                        self.canvases[5].axes.set_ylabel('Intensity ')
                        self.canvases[5].axes.set_title("Reflectance",color='w')
                        [t.set_color('w') for t in self.canvases[5].axes.xaxis.get_ticklabels()]
                        [t.set_color('w') for t in self.canvases[5].axes.yaxis.get_ticklabels()]
                        self.plot_datas[5] = self.reflectance[1::]
                        if self.reference_plots[5] is None:
                            plot_refs = self.canvases[5].axes.plot(self.wavelength[1::],self.reflectance[1::], color=(0,1,0.29))
                            self.reference_plots[5] = plot_refs[0]	
                        else:
                            self.reference_plots[5].set_ydata(self.reflectance[1::])
                        self.canvases[5].draw()
                        # min_y = min(self.reflectance[min(wAB):max(wAB)])
                        # max_y = max(self.reflectance[min(wAB):max(wAB)])
                        # self.ui.lineEdit_2.setText("Measurement On " + str(max_y) + " " + str(min_y))
                        self.canvases[8].axes.set_ylim(ymin = min_y, ymax= max_y)
                        self.canvases[8].axes.set_xlabel('Wavelength (nm)')
                        self.canvases[8].axes.set_ylabel('Intensity ')
                        self.canvases[8].axes.set_title("Reflectance (A-B)",color='w')
                        [t.set_color('w') for t in self.canvases[8].axes.xaxis.get_ticklabels()]
                        [t.set_color('w') for t in self.canvases[8].axes.yaxis.get_ticklabels()]
                        self.plot_datas[8] = self.reflectance[min(wAB):max(wAB)]
                        if self.reference_plots[8] is None:
                            plot_refs = self.canvases[8].axes.plot(self.wavelength[min(wAB):max(wAB)],self.reflectance[min(wAB):max(wAB)], color=(0,1,0.29))
                            self.reference_plots[8] = plot_refs[0]	
                        else:
                            self.reference_plots[8].set_ydata(self.reflectance[min(wAB):max(wAB)])
                        self.canvases[8].draw()

                        wL687 = (self.Eout_right_687[0] - self.Ein_687[0])/(self.Eout_right_687[0] - self.Eout_left_687[0])
                        wL760 = (self.Eout_right_760[0] - self.Ein_760[0])/(self.Eout_right_760[0] - self.Eout_left_760[0])
                        wR687 = (self.Ein_687[0] - self.Eout_left_687[0])/(self.Eout_right_687[0] - self.Eout_left_687[0])
                        wR760 = (self.Ein_760[0] - self.Eout_left_760[0])/(self.Eout_right_760[0] - self.Eout_left_760[0])
                        
                        FLD1 = (((wL687 * self.Eout_left_687[1] + wR687 * self.Eout_right_687[1]) * self.Lin_687[1])-(self.Ein_687[1]*(wL687 * self.Lout_left_687[1] + wR687 * self.Lout_right_687[1])))/((wL687 * self.Eout_left_687[1] + wR687 * self.Eout_right_687[1])-self.Ein_687[1])
                        FLD2 = (((wL760 * self.Eout_left_760[1] + wR760 * self.Eout_right_760[1]) * self.Lin_760[1])-(self.Ein_760[1]*(wL760 * self.Lout_left_760[1] + wR760 * self.Lout_right_760[1])))/((wL760 * self.Eout_left_760[1] + wR760 * self.Eout_right_760[1])-self.Ein_760[1])
                        
                        # FLD1 = ((np.mean([self.Eout_left_687[1], self.Eout_right_687[1]]) * self.Lin_687[1])-(self.Ein_687[1]*np.mean([self.Lout_left_687[1], self.Lout_right_687[1]])))/(np.mean([self.Eout_left_687[1], self.Eout_right_687[1]])-self.Ein_687[1])
                        # FLD2 = ((np.mean([self.Eout_left_760[1], self.Eout_right_760[1]]) * self.Lin_760[1])-(self.Ein_760[1]*np.mean([self.Lout_left_760[1], self.Lout_right_760[1]])))/(np.mean([self.Eout_left_760[1], self.Eout_right_760[1]])-self.Ein_760[1])
                        
                        self.ui.lineEdit_13.setText(str(round(FLD1,3)))
                        self.ui.lineEdit_15.setText(str(round(FLD2,3)))
                        if self.if_range_changed:
                            # print(self.if_range_changed)
                            # Edata_calib = np.multiply(np.subtract(self.intensity_E, self.backgroundIntensity), self.calibCoeff_E)
                            y_data = self.plot_datas[7]
                            min_y = min(y_data[min(wAB):max(wAB)])
                            max_y = max(y_data[min(wAB):max(wAB)])
                            # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
                            self.canvases[7].axes.set_ylim(ymin = min_y, ymax= max_y)
                            self.canvases[7].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax = self.wavelength[max(wAB)])
                            self.canvases[7].axes.set_xlabel('Wavelength (nm)')
                            self.canvases[7].axes.set_ylabel('Intensity ')
                            self.canvases[7].axes.set_title("Calib L (A-B)",color='w')
                            [t.set_color('w') for t in self.canvases[7].axes.xaxis.get_ticklabels()]
                            [t.set_color('w') for t in self.canvases[7].axes.yaxis.get_ticklabels()]
                            
                            self.canvases[7].axes.plot(self.wavelength, y_data,color=(0,1,0.29), alpha = 0.4)
                                # print(self.reference_plots[6].get_ydata())
                            self.canvases[7].draw()
                            self.if_range_changed = False
                        # self.ui.lineEdit_15.setText(str(round(FLD,2)))
            if self.isStopped and self.if_range_changed:
                print("stopped but changed")
                wAB = [index for index,value in enumerate(self.wavelength) if (value > self.plotRangeLeft and value < self.plotRangeRight)]
                if (self.plot_datas[7] is not None):
                    y_data = self.plot_datas[4]
                    min_y = min(y_data[min(wAB):max(wAB)])
                    max_y = max(y_data[min(wAB):max(wAB)])
                    # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
                    self.canvases[7].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[7].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax = self.wavelength[max(wAB)])
                    self.canvases[7].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[7].axes.set_ylabel('Intensity ')
                    self.canvases[7].axes.set_title("Calib L (A-B)",color='w')
                    [t.set_color('w') for t in self.canvases[7].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[7].axes.yaxis.get_ticklabels()]
                    
                    self.canvases[7].axes.plot(self.wavelength, y_data,color=(0,1,0.29), alpha = 0.4)
                        # print(self.reference_plots[6].get_ydata())
                    self.canvases[7].draw()
                    self.if_range_changed = False  
                if (self.plot_datas[6] is not None):
                    y_data = self.plot_datas[3]
                    min_y = min(y_data[min(wAB):max(wAB)])
                    max_y = max(y_data[min(wAB):max(wAB)])
                    # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
                    self.canvases[6].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[6].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax = self.wavelength[max(wAB)])
                    self.canvases[6].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[6].axes.set_ylabel('Intensity ')
                    self.canvases[6].axes.set_title("Calib E (A-B)",color='w')
                    [t.set_color('w') for t in self.canvases[6].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[6].axes.yaxis.get_ticklabels()]
                    
                    self.canvases[6].axes.plot(self.wavelength, y_data,color=(0,1,0.29), alpha = 0.4)
                        # print(self.reference_plots[6].get_ydata())
                    self.canvases[6].draw()
                    self.if_range_changed = False
                if (self.plot_datas[8] is not None):
                    y_data = self.plot_datas[5]
                    min_y = min(y_data[min(wAB):max(wAB)])
                    max_y = max(y_data[min(wAB):max(wAB)])
                    # self.ui.lineEdit_2.setText("Measurement On " + str(max_y))
                    self.canvases[8].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[8].axes.set_xlim(xmin = self.wavelength[min(wAB)], xmax = self.wavelength[max(wAB)])
                    self.canvases[8].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[8].axes.set_ylabel('Intensity ')
                    self.canvases[8].axes.set_title("Reflectance (A-B)",color='w')
                    [t.set_color('w') for t in self.canvases[8].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[8].axes.yaxis.get_ticklabels()]
                    
                    self.canvases[8].axes.plot(self.wavelength, y_data,color=(0,1,0.29), alpha = 0.4)
                        # print(self.reference_plots[6].get_ydata())
                    self.canvases[8].draw()
                    self.if_range_changed = False
        except Exception as e:
            print("Error: " , e)
            pass
    def getReflectance(self, E, L):
        reference_percentage = 100
        if self.if_L:
            E = [a-b for a,b in zip(E, self.backgroundIntensity)]
        else:
            L = [a-b for a,b in zip(L, self.backgroundIntensity)]
            
        E_calib = [a * b for a,b in zip(E, self.calibCoeff_E)]
        L_calib = [a * b for a,b in zip(L, self.calibCoeff_L)]
        reflectance = [l/(e/(reference_percentage/100)) for l, e in zip(L_calib,E_calib)]
        # print(reflectance)
        return reflectance
    def getReflectance2(self, E, L):
        reference_percentage = 100
        
        E_calib = [a * b for a,b in zip(E, self.calibCoeff_E)]
        L_calib = [a * b for a,b in zip(L, self.calibCoeff_L)]
        reflectance = [l/(e/(reference_percentage/100)) for l, e in zip(L_calib,E_calib)]
        # print(reflectance)
        return reflectance
    def getResultsMin(self, L, a,b):
        if a == b:
            index_min = np.argmin(np.abs(np.subtract(self.wavelength, a)))
            return [self.wavelength[index_min], L[index_min]]
        else:
            wAB = [index for index,value in enumerate(self.wavelength) if (value > a and value < b)]
            index_min = np.argmin(L[min(wAB):max(wAB)])
            w_temp = self.wavelength[min(wAB):max(wAB)]
            # print(index_min)
            return [w_temp[index_min],np.min(L[min(wAB):max(wAB)])]
    def getResultsMax(self, L, a,b):
        if a == b:
            index_max = np.argmin(np.abs(np.subtract(self.wavelength, a)))
            return [self.wavelength[index_max], L[index_max]]
        else:
            wAB = [index for index,value in enumerate(self.wavelength) if (value > a and value < b)]
            index_min = np.argmax(L[min(wAB):max(wAB)])
            w_temp = self.wavelength[min(wAB):max(wAB)]
            # print(index_min)
            return [w_temp[index_min],np.max(L[min(wAB):max(wAB)])]

#This creates the actual window when Python runs and keeps it running until 
# you close the window
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    # window.show()
    sys.exit(app.exec_())