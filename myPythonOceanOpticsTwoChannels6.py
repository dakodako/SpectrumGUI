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


import sys
import os
import time
import numpy as np
import queue

save_counter = 0


pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'k')
class Worker(QtCore.QRunnable):

	def __init__(self, function, *args, **kwargs):
		super(Worker, self).__init__()
		self.function = function
		self.args = args
		self.kwargs = kwargs

	@pyqtSlot()
	def run(self):
		self.function(*self.args, **self.kwargs)

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
    
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('main6.ui',self)
        # self.title = 'HyperSens Spectrometer Software'
        self.ui.setWindowTitle('HyperSens Spectrometer Software')
        self.device_list = []
        self.ui.comboBox_2.addItems(self.device_list)
        self.ui.comboBox_2.setCurrentIndex(0)
        
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
        self.ui.pushButton_18.setEnabled(False)
        self.ui.pushButton_19.setEnabled(False)
        self.ui.pushButton_20.setEnabled(False)
        self.ui.checkBox.setCheckable(True)
        self.ui.checkBox.clicked.connect(self.EOnlyFibreMode)
        self.ui.checkBox_3.setCheckable(True)
        self.ui.checkBox_3.clicked.connect(self.LOnlyFibreMode)
        self.ui.checkBox_4.setCheckable(True)
        self.ui.checkBox_4.setChecked(True)
        # self.BothFibreMode()
        self.ui.checkBox_4.clicked.connect(self.BothFibreMode)
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
        # self.ui.pushButton_16.clicked.connect(self.stopWorker)
        self.ui.pushButton_19.clicked.connect(self.stopWorker)
        ######### get calibration file #########
        self.ui.pushButton_2.clicked.connect(self.open_calib_file_L) # get calibration file for L
        self.ui.pushButton_3.clicked.connect(self.open_calib_file_E) # get calibration file for E
        # self.ui.pushButton_4.setCheckable(True)
        # self.ui.pushButton_7.setCheckable(True)
        self.applyCalibE = False
        self.applyCalibL = False
        # self.ui.pushButton_4.clicked.connect(self.applyCalibration)
        # self.ui.pushButton_7.clicked.connect(self.applyCalibration)
        ######### Save ########
        # self.ui.pushButton_10.setCheckable(True)
        # self.ui.pushButton_10.clicked.connect(self.saveSpectra)
        self.ui.pushButton_20.clicked.connect(self.saveSpectra)
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
        self.intensity_E = None
        self.intensity_L = None 
        self.backgroundIntensity = None  
        self.calib_file_name_E = None 
        self.calib_file_name_L = None 
        self.updateRate = 50 # millisecond
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.updateRate)
        
        self.timer.timeout.connect(self.plotSpectra)
        self.timer.start()
        self.worker = None 
        self.isStopped = True
        self.show()
    def updateResults(self):
        self.Ein_687 = self.getResultsMin(self.plot_datas[3], self.InRange1Min, self.InRange1Max)
        self.Lin_687 = self.getResultsMin(self.plot_datas[4], self.InRange1Min, self.InRange1Max)
        self.Eout_left_687 = self.getResultsMax(self.plot_datas[3], self.OutLeftRange1Min, self.OutLeftRange1Max)
        self.Eout_right_687 = self.getResultsMax(self.plot_datas[3], self.OutRightRange1Min, self.OutRightRange1Max)
        self.Lout_left_687 = self.getResultsMax(self.plot_datas[4], self.OutLeftRange1Min, self.OutLeftRange1Max)
        self.Lout_right_687 = self.getResultsMax(self.plot_datas[4], self.OutRightRange1Min, self.OutRightRange1Max)
        FLD1 = ((np.mean([self.Eout_left_687[1], self.Eout_right_687[1]]) * self.Lin_687[1])-(self.Ein_687[1]*np.mean([self.Lout_left_687[1], self.Lout_right_687[1]])))/(np.mean([self.Eout_left_687[1], self.Eout_right_687[1]])-self.Ein_687[1])
        # FLD2 = ((np.mean([self.Eout_left_760[1], self.Eout_right_760[1]]) * self.Lin_760[1])-(self.Ein_760[1]*np.mean([self.Lout_left_760[1], self.Lout_right_760[1]])))/(np.mean([self.Eout_left_760[1], self.Eout_right_760[1]])-self.Ein_760[1])
        self.ui.lineEdit_13.setText(str(round(FLD1,3))) 
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
                if self.isIntTimeChanged:
                    if self.if_L:
                        self.spec.integration_time_micros(self.int_time_L)
                    else:
                        self.spec.integration_time_micros(self.int_time_E)
                    self.isIntTimeChanged = False
                QtWidgets.QApplication.processEvents()
                self.intensity = self.getSpectra()
                if self.if_L:
                    self.intensity_L = self.intensity
                else:
                    self.intensity_E = self.intensity
                if max(self.intensity) > self.spec.max_intensity * 0.9:
                    self.ui.pushButton_5.setStyleSheet("QPushButton {background-color: rgb(255,0,0)}")
                    self.ui.lineEdit_2.setText("Saturation detected, integration time optimization recommended.")
                else:
                    self.ui.pushButton_5.setStyleSheet("QPushButton {background-color: rgb(255,255,255)}")
                    
                input_data = [a - b for a, b in zip(self.intensity, self.backgroundIntensity)] 
                self.q.put(input_data)
                if self.isStopped:
                    break
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
        for i in range(0,9):
            # print("Close canvas")
            self.canvases[i].axes.clear()
        # for i in range(0,3):
        #     for j in range(0,3):
        #         self.canvas.axes[i,j].clear()
        self.isStopped = False
        self.worker = Worker(self.startMeasurement,)
        self.threadpool.start(self.worker)
        print('Start')
        for i in range(0,9):
            self.reference_plots[i] = None
            # self.plot_datas[i] = None
        # self.plot_datas[0] = None
        # self.plot_datas[3] = None
        # self.plot_datas[6] = None
        self.timer.setInterval(int(self.updateRate))
    
    def stopWorker(self):
        self.isStopped = True
        self.ui.pushButton_18.setEnabled(True)
        self.ui.pushButton.setEnabled(True)
        self.ui.pushButton_5.setEnabled(True)
        pg.QtGui.QGuiApplication.processEvents() 
        if self.if_L is not True:
            self.reference_plots[0].set_alpha(0.4)
            self.reference_plots[3].set_alpha(0.4)
            self.reference_plots[6].set_alpha(0.4)
            self.canvases[0].draw()
            self.canvases[3].draw()
            self.canvases[6].draw()
        else:
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
        time.sleep(1) #This pauses the program for 3 seconds
        self.threadpool.thread().quit()
        sys.exit()
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
    def saveSpectra(self):
        if self.if_L:
            intensityL = np.subtract(self.intensity_L, self.backgroundIntensity)
            intensityL_calib = np.multiply(intensityL, self.calibCoeff_L)
            if self.intensity_E is not None:
                intensityE =  np.subtract(self.intensity_E, self.backgroundIntensity)
                intensityE_calib = np.multiply(intensityE, self.calibCoeff_E)
        else:
            intensityE = np.subtract(self.intensity_E, self.backgroundIntensity)
            intensityE_calib = np.multiply(intensityE, self.calibCoeff_E)
            if self.intensity_L is not None:
                intensityL =  np.subtract(self.intensity_L, self.backgroundIntensity)
                intensityL_calib = np.multiply(intensityL, self.calibCoeff_L)
        # reflectance = np.divide(intensityL_calib,intensityE_calib)
        control_info = "Integration time (L): " + str(self.int_time_L) + ", Integration time (E): " + str(self.int_time_E) + ", Scans to average (L): " + str(self.scans_to_avg_L) + ", Scans to average (E): " + str(self.scans_to_avg_E) + '\n'
        filename = self.directoryPath + '\\'+self.ui.lineEdit_14.text() + '_'+self.spec.model+'_'+str(self.save_counter)+'_'+ datetime.now().strftime("%d-%m-%Y-%H-%M-%S")+'.txt'
        outfile = open(filename,'w')
        outfile.write("Wavelength, Intensity (L), intensity calibrated (L), Intensity (E), Intensity calibrated (L), Background, Reflectance " + control_info)
        for idx in range(0,len(self.wavelength)):
            outfile.write(str(round(self.wavelength[idx],4)) + ',' + str(round(intensityL[idx],2)) + ',' + str(round(intensityL_calib[idx],2)) + ',' + str(round(intensityE[idx],2)) + ',' + str(round(intensityE_calib[idx],2)) + ',' + str(round(self.backgroundIntensity[idx],2)) + ',' + str(round(self.reflectance[idx],2)) + '\n')
        outfile.close()
        self.save_counter = self.save_counter + 1
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
            self.ui.spinBox_2.setMaximum(50)
            self.ui.spinBox_2.setValue(10)
            self.scans_to_avg_L = 1
            self.ui.spinBox_5.setMinimum(1)
            self.ui.spinBox_5.setMaximum(50)
            self.ui.spinBox_5.setValue(10)
            self.scans_to_avg_E = 1
            # print("maximum intensity: " + str(self.spec.max_intensity))
            self.wavelength = self.spec.wavelengths()
            ####### default measurement #######
            self.isIntTimeChanged = False
            self.BothFibreMode()
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
            # self.calib_file_name_E = [0.5] * len(self.wavelength)
            self.calibCoeff_L = self.read_calib_file(self.calib_file_name_L)
            self.calibCoeff_E = self.read_calib_file(self.calib_file_name_E)
            self.applyCalibL = True
            self.applyCalibE = True
            # self.calibCoeff_E = self.calibCoeff_L
            self.isStopped = True
            self.saveData = False
            self.save_counter = 1
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
            self.ui.pushButton_20.setEnabled(True)
            ########## results calculation #########
            # In @ 687
            self.doubleSpinBox_3.setMinimum(min(self.wavelength))
            self.doubleSpinBox_3.setMaximum(max(self.wavelength))
            self.doubleSpinBox_3.setValue(687)

            self.doubleSpinBox_4.setMinimum(min(self.wavelength))
            self.doubleSpinBox_4.setMaximum(max(self.wavelength))
            self.doubleSpinBox_4.setValue(687)
            self.setInRange1()
            # In @ 760
            self.doubleSpinBox.setMinimum(min(self.wavelength))
            self.doubleSpinBox.setMaximum(max(self.wavelength))
            self.doubleSpinBox.setValue(760)

            self.doubleSpinBox_2.setMinimum(min(self.wavelength))
            self.doubleSpinBox_2.setMaximum(max(self.wavelength))
            self.doubleSpinBox_2.setValue(760)
            self.setInRange2()
            # Out left @ 680
            self.doubleSpinBox_5.setMinimum(min(self.wavelength))
            self.doubleSpinBox_5.setMaximum(max(self.wavelength))
            self.doubleSpinBox_5.setValue(675)

            self.doubleSpinBox_6.setMinimum(min(self.wavelength))
            self.doubleSpinBox_6.setMaximum(max(self.wavelength))
            self.doubleSpinBox_6.setValue(675)
            self.setOutLeftRange1()
            # Out left @ 760
            self.doubleSpinBox_7.setMinimum(min(self.wavelength))
            self.doubleSpinBox_7.setMaximum(max(self.wavelength))
            self.doubleSpinBox_7.setValue(757)

            self.doubleSpinBox_8.setMinimum(min(self.wavelength))
            self.doubleSpinBox_8.setMaximum(max(self.wavelength))
            self.doubleSpinBox_8.setValue(757)
            self.setOutLeftRange2()
            # Out right @ 687
            self.doubleSpinBox_9.setMinimum(min(self.wavelength))
            self.doubleSpinBox_9.setMaximum(max(self.wavelength))
            self.doubleSpinBox_9.setValue(690)

            self.doubleSpinBox_10.setMinimum(min(self.wavelength))
            self.doubleSpinBox_10.setMaximum(max(self.wavelength))
            self.doubleSpinBox_10.setValue(690)
            self.setOutRightRange1()
            # Out right @ 760
            self.doubleSpinBox_11.setMinimum(min(self.wavelength))
            self.doubleSpinBox_11.setMaximum(max(self.wavelength))
            self.doubleSpinBox_11.setValue(775)
        
            self.doubleSpinBox_12.setMinimum(min(self.wavelength))
            self.doubleSpinBox_12.setMaximum(max(self.wavelength))
            self.doubleSpinBox_12.setValue(775)
            self.setOutRightRange2()
            self.if_range_changed = False
            self.startWorker()
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
            
    def setSpecIntTime(self):
        self.isIntTimeChanged = True
        if self.if_L:
            self.int_time_L = self.ui.spinBox.value() * 1000
            if self.int_time_L < self.spec.integration_time_micros_limits[0] | self.int_time_L > self.spec.integration_time_micros_limits[1]:
                print('Integration time is too short or too long')
        else:
            self.int_time_E = self.ui.spinBox_4.value() * 1000
            if self.int_time_E < self.spec.integration_time_micros_limits[0] | self.int_time_E > self.spec.integration_time_micros_limits[1]:
                print('Integration time is too short or too long')
        
        #for x in range(1,4):
            #time.sleep(0.5)
            #self.progressBar.setValue(x/3*100)
        # sb.setIntegrationTime(time)
        
        # self.spec.integration_time_micros(time)
        if self.if_L:
            self.ui.lineEdit_2.setText("Integration time (L) has been set to "+ str(self.ui.spinBox.value()) + " ms")
            self.ui.pushButton_12.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
        else:
            self.ui.lineEdit_2.setText("Integration time (E) has been set to "+ str(self.ui.spinBox_4.value()) + " ms")
            self.ui.pushButton_9.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
       
    def setScansToAvg(self):
        if self.if_L:
            self.scans_to_avg_L = self.ui.spinBox_2.value()
            self.current_scans_to_avg = self.scans_to_avg_L
            self.ui.lineEdit_2.setText("Scans to average (L) has been set to "+ str(self.scans_to_avg_L))
            self.ui.pushButton_14.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
        else:
            self.scans_to_avg_E = self.ui.spinBox_5.value()
            self.current_scans_to_avg = self.scans_to_avg_E
            self.ui.lineEdit_2.setText("Scans to average (E) has been set to "+ str(self.scans_to_avg_E))
            self.ui.pushButton_13.setStyleSheet("QPushButton {background-color: rgb(85,225,0)}")
        
        # scans = self.scansToAvg.value()
        # self.scans_to_avg = scans
        # self.lineEdit_2.setText("Scans to average has been set to "+ str(scans))
        
       
        # print(scans)

    def EOnlyFibreMode(self):
        if self.ui.checkBox.isChecked():
            self.ui.checkBox_2.setEnabled(False)
            self.ui.checkBox_4.setEnabled(False)
            self.ui.checkBox_3.setEnabled(False)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_9.setEnabled(True)
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_13.setEnabled(True)
            self.if_L = False
        else:
            self.ui.checkBox_4.setEnabled(True)
            self.ui.checkBox_3.setEnabled(True)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_13.setEnabled(False)
    def LOnlyFibreMode(self):
        if self.ui.checkBox_3.isChecked():
            self.ui.checkBox_2.setEnabled(False)
            self.ui.checkBox.setEnabled(False)
            self.ui.checkBox_4.setEnabled(False)
            self.ui.pushButton_12.setEnabled(True)
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_14.setEnabled(True)
            self.ui.pushButton_13.setEnabled(False)
            self.if_L = True
        else:
            self.ui.checkBox.setEnabled(True)
            self.ui.checkBox_4.setEnabled(True)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_13.setEnabled(False)
    def BothFibreMode(self):
        if self.ui.checkBox_4.isChecked():
            self.ui.checkBox_2.setEnabled(True)
            self.ui.checkBox.setEnabled(False)
            self.ui.checkBox_3.setEnabled(False)
            self.ui.pushButton_12.setEnabled(True)
            self.ui.pushButton_9.setEnabled(True)
            self.ui.pushButton_14.setEnabled(True)
            self.ui.pushButton_13.setEnabled(True)
            if self.ui.checkBox_2.isChecked():
                self.if_L = False
            else:
                self.if_L = True
        else:
            self.ui.checkBox.setEnabled(True)
            self.ui.checkBox_3.setEnabled(True)
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_13.setEnabled(False)
    def trigger_switched(self):
        if self.ui.checkBox_2.isChecked():
            self.if_L = False
            self.ui.lineEdit_2.setText("E Fibre selected.")
            self.ui.pushButton_12.setEnabled(False)
            self.ui.pushButton_9.setEnabled(True)
            self.ui.pushButton_14.setEnabled(False)
            self.ui.pushButton_13.setEnabled(True)
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
            # self.plot_datas[7] = None
            # self.reference_plots[7] = None
            # self.canvases[7].axes.clear()
            # self.ui.spinBox.setEnabled(False)
            # self.ui.spinBox_4.setEnabled(True)
            # self.ui.pushButton_12.setEnabled(False)
            # self.ui.pushButton_9.setEnabled(True)
        else:
            self.if_L = True
            self.ui.lineEdit_2.setText("L Fibre selected.")
            self.ui.pushButton_12.setEnabled(True)
            self.ui.pushButton_9.setEnabled(False)
            self.ui.pushButton_14.setEnabled(True)
            self.ui.pushButton_13.setEnabled(False)
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
        # print(self.if_L)
            # self.ui.spinBox.setEnabled(True)
            # self.ui.spinBox_4.setEnabled(False)
            # self.ui.pushButton_12.setEnabled(True)
            # self.ui.pushButton_9.setEnabled(False)
    def startOptimize(self):
        print('Start optimization')
        # intensity = self.spec.intensities()
        intensity = self.spec.intensities()
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
            intensity = self.spec.intensities()
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

    def getSpectra(self):
        scans = self.current_scans_to_avg
        # t = self.integrationTime.value()
        x = self.wavelength
        spectrum_final = [0] * len(x)
        for iterator in range(1,scans+1):
            inten_temp = self.spec.intensities()
            # print(iterator)
            spectrum_final = spectrum_final + inten_temp
        # spectrum_final = spectrum_final/scans
        # print(spectrum_final)
        spectrum_final = [s / scans for s in spectrum_final]
        return spectrum_final
        
    def measureBackground(self):
        # if self.if_L:
        #     print("inte time: " + str(self.int_time_L))
        #     self.spec.integration_time_micros(int(self.ui.spinBox.value() * 1000))
        # else:
        #     print("inte time: " + str(self.int_time_E))
        #     self.spec.integration_time_micros(int(self.ui.spinBox_4.value() * 1000))
        # wavelength = self.spec.wavelengths()
        # backgroundIntensity = self.getSpectra()
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
    def stopSpectra(self):
        self.isStopped = True
        self.intensity = []
        
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
                    min_y = min(self.ydata_calib[1::])
                    max_y = max(self.ydata_calib[1::])
                    self.canvases[4].axes.set_ylim(ymin = min_y, ymax= max_y)
                    self.canvases[4].axes.set_xlabel('Wavelength (nm)')
                    self.canvases[4].axes.set_ylabel('Intensity ')
                    self.canvases[4].axes.set_title("Calib L",color='w')
                    [t.set_color('w') for t in self.canvases[4].axes.xaxis.get_ticklabels()]
                    [t.set_color('w') for t in self.canvases[4].axes.yaxis.get_ticklabels()]
                    self.plot_datas[4] = self.ydata_calib
                    if self.reference_plots[4] is None:
                        plot_refs = self.canvases[4].axes.plot(self.xdata,self.ydata_calib, color=(0,1,0.29), alpha = 1)
                        self.reference_plots[4] = plot_refs[0]	
                    else:
                        self.reference_plots[4].set_ydata(self.ydata_calib)
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
                        self.reflectance = self.getReflectance( self.intensity_E, self.ydata)
                        # min_y = np.divide(np.max(self.ydata_calib),np.min(np.multiply(np.subtract(self.intensity_E[1::], self.backgroundIntensity[1::]), self.calibCoeff_E[1::])))
                        # max_y = np.nanmax(self.reflectance[1::])
                        # min_y = np.nanmin(self.reflectance[self.reflectance != np.NINF])
                        max_y = 10
                        min_y = -10
                        # max_y = np.divide(np.max(self.ydata_calib),np.max(np.multiply(np.subtract(self.intensity_E[1::], self.backgroundIntensity[1::]), self.calibCoeff_E[1::])))
                        # print(min_y)
                        # print(max_y)
                        self.canvases[5].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
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
                        self.canvases[8].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
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
                        
                        FLD1 = ((np.mean([self.Eout_left_687[1], self.Eout_right_687[1]]) * self.Lin_687[1])-(self.Ein_687[1]*np.mean([self.Lout_left_687[1], self.Lout_right_687[1]])))/(np.mean([self.Eout_left_687[1], self.Eout_right_687[1]])-self.Ein_687[1])
                        FLD2 = ((np.mean([self.Eout_left_760[1], self.Eout_right_760[1]]) * self.Lin_760[1])-(self.Ein_760[1]*np.mean([self.Lout_left_760[1], self.Lout_right_760[1]])))/(np.mean([self.Eout_left_760[1], self.Eout_right_760[1]])-self.Ein_760[1])
                        
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
                    min_y = min(self.ydata_calib[1::])
                    max_y = max(self.ydata_calib[1::])
                    self.canvases[3].axes.set_ylim(ymin = min_y, ymax= max_y)
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
                        self.reflectance = self.getReflectance(self.ydata, self.intensity_L)
                        # min_y = np.divide(np.min(np.multiply(np.subtract(self.intensity_L[1::], self.backgroundIntensity[1::]), self.calibCoeff_L[1::])),np.max(self.ydata_calib[1::]))
                        # max_y = np.divide(np.max(np.multiply(np.subtract(self.intensity_L[1::], self.backgroundIntensity[1::]), self.calibCoeff_L[1::])),np.min(self.ydata_calib[1::]))
                        # max_y = np.nanmax(self.reflectance[1::])
                        # min_y = np.nanmin(self.reflectance[self.reflectance != np.NINF])
                        # max_y = np.nanmax(self.reflectance[self.reflectance != np.Inf])
                        # print("Reflectance max: " + str(max_y))
                        # min_y = np.nanmin(self.reflectance[self.reflectance != np.NINF and self.reflectance != np.Inf])
                        # print("Reflectance min: " + str(np.nanmin(self.reflectance[self.reflectance != np.NINF])))
                        min_y = -10
                        max_y = 10
                        self.canvases[5].axes.set_ylim(ymin = min_y + 3 * min_y, ymax= max_y + 3 * max_y)
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
                        FLD1 = ((np.mean([self.Eout_left_687[1], self.Eout_right_687[1]]) * self.Lin_687[1])-(self.Ein_687[1]*np.mean([self.Lout_left_687[1], self.Lout_right_687[1]])))/(np.mean([self.Eout_left_687[1], self.Eout_right_687[1]])-self.Ein_687[1])
                        FLD2 = ((np.mean([self.Eout_left_760[1], self.Eout_right_760[1]]) * self.Lin_760[1])-(self.Ein_760[1]*np.mean([self.Lout_left_760[1], self.Lout_right_760[1]])))/(np.mean([self.Eout_left_760[1], self.Eout_right_760[1]])-self.Ein_760[1])
                        
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