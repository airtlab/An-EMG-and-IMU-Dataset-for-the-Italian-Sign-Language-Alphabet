import wx
import os
import shutil
import psutil
import myo
from myo import *
import time
import datetime
import uuid
import json
import threading
from threading import Thread
from keras.models import load_model
from keras.models import model_from_json
import numpy as np


# class that listens to Myo Armband events
class Listener(myo.DeviceListener):

    device_name = None
    battery = None

    def __init__(self, m):
        super().__init__()
        self.manager = m
        self.emg = []
        self.data = {}


    # connection event
    def on_connected(self, event:Event):
        self.manager.connecting = False
        self.manager.connected = True
        event.device.stream_emg(True)
        event.device.request_battery_level()
        self.device_name = event.device_name


    # disconnection event
    def on_disconnected(self, event:Event):
        self.manager.connected = False


    # emg signal event
    def on_emg(self, event:Event):
        self.emg = event.emg


    # imu signal event
    def on_orientation(self, event:Event):
        self.data = {
            "gyroscope": [event.gyroscope.x, event.gyroscope.y, event.gyroscope.z], 
            "acceleration": [event.acceleration.x, event.acceleration.y, event.acceleration.z], 
            "orientation": [event.orientation.x, event.orientation.y, event.orientation.z, event.orientation.w]
        }


    # battery level event
    def on_battery_level(self, event):
        self.battery = event.battery_level


    # returns the device name and the remaining battery level to the various panels
    def get(self):
        return self.device_name, self.battery


# main windows
# it is used to destroy the panels that are displayed above and to create new ones
# it is destroyed only with a closing event
class MainFrame(wx.Frame):
    myo = None
    connected = False
    connecting = False
    stop = False

    def __init__(self):
        wx.Frame.__init__(self, parent=None)
        
        self.create_working_directory()

        # tries to connect to the device
        self.connection(self)

        # creates the panel Main Menu
        self.main_menu = MainMenu(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.main_menu, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.SetSize((360, 480))
        self.SetTitle('Sign Language')
        self.Centre()


    # creates the folders necessary to contain the dataset and the neural network
    def create_working_directory(self):
        path = os.getcwd()
        dataset_directory = path + '\\Dataset'
        network_directory = path + '\\NeuralNetwork'

        if os.path.exists(dataset_directory) == False:
            try:
                os.mkdir(dataset_directory)
            except OSError:
                wx.MessageBox("Error during directory creation %s" % dataset_directory, "Info", wx.OK|wx.ICON_INFORMATION)

        if os.path.exists(network_directory) == False:
            try:
                os.mkdir(network_directory)
            except OSError:
                wx.MessageBox("Error during directory creation %s" % network_directory, "Info", wx.OK|wx.ICON_INFORMATION)

    
    
    # if myo is not yet initialized, initialize it, i.e. connect it to the device SDK
    # The bin folder of the myo64.dll SDK must be in the system PATH
    # otherwise pass the path of the bin folder as an argument to myo.init ()
    # if the device is not yet connected and is not connecting
    # the procedure for listening to the device starts
    def connection(self, e):
        if not self.myo:
            myo.init()
        if not self.connected and not self.connecting:
            self.connecting = True
            self.run()


    
    # create the listener that listens for events from the Myo Armband
    # if the device is connected, set a variable to True
    # this variable is checked and if it is set, the application starts normally
    # if it is not set, display an error message
    def run(self):
        self.listener = Listener(self)

        self.hub = myo.Hub()
        
        self.loop = Thread(target=self.run_loop)
        self.loop.start()
        time.sleep(2) # wait for 2 sec, otherwise the listener cannot receive the device connection event in time

        if self.connected == False:
            self.connecting = False
            wx.MessageBox("Device not connected", "Info", wx.OK|wx.ICON_INFORMATION)


    # thread that starts to listen for an event
    # thread is stopped only when the program is closed
    def run_loop(self):
        try:
            while self.hub.run(self.listener.on_event, 500):
                if self.stop:
                    self.stop = False
                    break
        except:
            self.stop = True


    # if the device is not connected in the Main Menu, it is given the possibility to connect it throught the "Connect" button
    # if "Connect" is pressed, this function starts and tries to establish the connection to the device
    def onConnectMenu(self, e, sender):
        if not self.connected and not self.connecting:
            self.connecting = True
            self.run()
            if self.connected == True:
                sender.Destroy()
                self.new_main_menu = MainMenu(self)
                self.sizer.Add(self.new_main_menu, 1, wx.EXPAND)
                self.SetSizer(self.sizer)
                self.Layout()
    

    # if the device is not connected in the Gestures List, it is given the possibility to connect it throught the "Connect" button
    # if "Connect" is pressed, this function starts and tries to establish the connection to the device
    def onConnectLista(self, e, sender):
        if not self.connected and not self.connecting:
            self.connecting = True
            self.run()
            if self.connected == True:
                sender.Destroy()
                self.new_gesture_list = GestureList(self)
                self.sizer.Add(self.new_gesture_list, 1, wx.EXPAND)
                self.SetSizer(self.sizer)
                self.Layout()


    # it starts when "Add new gesture" is pressed
    def onAddGesture(self, e, parent):
        if self.connected == True:
            parent.Destroy()

            self.menu_add_gesture = MenuAddGesture(self) 
            self.sizer.Add(self.menu_add_gesture, 1, wx.EXPAND)  
            self.SetSizer(self.sizer)

            self.Layout()
        else:
            wx.MessageBox("First connect the device", "Info", wx.OK|wx.ICON_INFORMATION)
        

    # it starts when you want to add a new acquisition from the Gestures List
    def onAddAcquisition(self, e, gesture, parent):
        if self.connected == True:
            parent.Destroy()

            self.acquisition = Acquisition(self, gesture)   
            self.sizer.Add(self.acquisition, 1, wx.EXPAND)
            self.SetSizer(self.sizer)

            self.Layout()
        else:
            wx.MessageBox("First connect the device", "Info", wx.OK|wx.ICON_INFORMATION)


    # it starts when "Close" is pressed
    def onClose(self, e):
        self.stop = True # close run_loop
        self.Close(True)
    

    # it starts when "Gestures List" is pressed
    def onListGesture(self, e, parent):
        path = os.getcwd() + '\\Dataset'
        gesture = os.listdir(path)
        if len(gesture) == 0:
            wx.MessageBox("There are no gesture yet", "Info", wx.OK|wx.ICON_INFORMATION)
        else:
            parent.Destroy()

            self.gesture_list = GestureList(self)
            self.sizer.Add(self.gesture_list, 1, wx.EXPAND)
            self.SetSizer(self.sizer)

            self.Layout()


    # it starts when "Confirmation" is pressed to confirm the gesture's name
    def onConf(self, e, gesture, parent):
        path = os.getcwd() + '\\Dataset\\'
        if os.path.exists(path + gesture.upper()):
            wx.MessageBox("The gesture is already present", "Info", wx.OK|wx.ICON_INFORMATION)
        else:
            try:
                os.makedirs(path + gesture.upper())
            except OSError:
                wx.MessageBox("Error during gesture creation, try again", "Info", wx.OK|wx.ICON_INFORMATION)

            parent.Destroy()

            self.acquisition = Acquisition(self, gesture.upper())   
            self.sizer.Add(self.acquisition, 1, wx.EXPAND)
            self.SetSizer(self.sizer)

            self.Layout()


    # it starts when "Training Model" is pressed
    def onTraining(self, e, parent):
        parent.Destroy()

        self.training = Training(self)   
        self.sizer.Add(self.training, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.Layout()
        

    # it starts when "Test Model" is pressed
    def onTest(self, e, parent):
        if self.connected == True:
            parent.Destroy()

            self.testing = Testing(self)   
            self.sizer.Add(self.testing, 1, wx.EXPAND)
            self.SetSizer(self.sizer)

            self.Layout()
        else:
            wx.MessageBox("First connect the device", "Info", wx.OK|wx.ICON_INFORMATION)


    # it starts when "Start" is pressed during model testing
    def onPredict(self, e, parent, model, weight):
        parent.Destroy()

        self.predict = Prediction(self, model, weight)   
        self.sizer.Add(self.predict, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.Layout()


    # it starts when "Back" is pressed
    # always returns to the main menu
    # TODO through a parameter you could see if it is possible to restore the previous panel and not always return to the main menu
    def onBack(self, e, parent):
        parent.Destroy()

        self.main_menu = MainMenu(self)
        self.sizer.Add(self.main_menu, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.Layout()
    

    # to make a new acquisition
    def reAcquisition(self, e, sender, gesture):
        sender.Destroy()

        self.acquisition = Acquisition(self, gesture)
        self.sizer.Add(self.acquisition, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.Layout()


    # when the test acquisition ends this function is activated automatically
    # it creates a new panel showing the predicted gesture
    def onResult(self, e, parent, prediction, model, weight):
        parent.Destroy()

        self.result = Result(self, prediction, model, weight)
        self.sizer.Add(self.result, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.Layout()


    # to make a new acquisition in the model testing
    def onRestart(self, e, parent, model, weight):
        parent.Destroy()

        self.predict = Prediction(self, model, weight)   
        self.sizer.Add(self.predict, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.Layout()



# panel that is launched at the start of the application
# panel that is launched each time the "Back" button is pressed
class MainMenu(wx.Panel):
    
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
    
        self.InitUI(parent)
        

    def InitUI(self, parent):
        self.text_name = wx.StaticText(self, label='Device: \n\n', pos=(20,20))
        self.text_name.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.battery_level = wx.StaticText(self, label='Battery: \n\n', pos=(260,20))
        self.battery_level.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        # if the device is connected, the text_name label with the name of the device
        # and the battery_level label with the percentage of the battery left
        if parent.connected == True:
            name, battery = parent.listener.get()
            self.text_name.SetLabel(self.text_name.GetLabel() + name)
            self.battery_level.SetLabel(self.battery_level.GetLabel() + str(battery) + "%")
        # if the device is not connected, it inserts the "Connect" button to allows a new connection to the device
        else:
            connect_button = wx.Button(self, label="Connect", pos=(140,140))
            connect_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onConnectMenu(event, self))

        im = wx.Image('images/myo.png', wx.BITMAP_TYPE_ANY)
        im.Rescale(120,120)
        image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im), pos=(115,10))

        st = wx.StaticLine(self, wx.ID_ANY, pos=(20,150), size=(300,2), style=wx.LI_HORIZONTAL)

        new_gesture_button = wx.Button(self, label='Add\n new gesture', pos=(20,180), size=(140,100))
        new_gesture_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onAddGesture(event, self))
        new_gesture_button.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        list_gesture_button = wx.Button(self, label='Gesture list', pos=(185,180), size=(140,100))
        list_gesture_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onListGesture(event, self))
        list_gesture_button.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        training_button = wx.Button(self, label='Train\nmodel', pos=(20,290), size=(140,100))
        training_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onTraining(event, self))
        training_button.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        test_button = wx.Button(self, label='Test\nmodel', pos=(185,290), size=(140,100))
        test_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onTest(event, self))
        test_button.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        close_button = wx.Button(self, label='Close', pos=(250,410))
        close_button.Bind(wx.EVT_BUTTON, parent.onClose)



# panel that is created if it is chosen "Add new Gesture" from Main Menu
class MenuAddGesture(wx.Panel):
    
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        self.InitUI(parent)


    def InitUI(self, parent):
        self.text_name = wx.StaticText(self, label='Device: \n\n', pos=(20,20))
        self.text_name.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.battery_level = wx.StaticText(self, label='Battery: \n\n', pos=(260,20))
        self.battery_level.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        name, battery = parent.listener.get()
        self.text_name.SetLabel(self.text_name.GetLabel() + name)
        self.battery_level.SetLabel(self.battery_level.GetLabel() + str(battery) + "%")
        
        im = wx.Image('images/myo.png', wx.BITMAP_TYPE_ANY)
        im.Rescale(120,120)
        image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im), pos=(115,10))

        st = wx.StaticLine(self, wx.ID_ANY, pos=(20,150), size=(300,2), style=wx.LI_HORIZONTAL)

        question = wx.StaticText(self, label='What name do you want to\n give to the new gesture?', pos=(80,180))
        question.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        resp = wx.TextCtrl(self, pos=(22,230), size=(300, 30))
        
        conf_button = wx.Button(self, label='Confirmation', pos=(135, 300))
        conf_button.Bind(wx.EVT_BUTTON, lambda event, gesture=resp.GetValue(), parent=parent: parent.onConf(event, resp.GetValue(), self))

        back_button= wx.Button(self, label='Back', pos=(20,410))
        back_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onBack(event, self))

        close_button = wx.Button(self, label='Close', pos=(250,410))
        close_button.Bind(wx.EVT_BUTTON, parent.onClose)




# panel that is created if it is chosen "Gestures List" from the Main Menu
class GestureList(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        self.InitUI(parent)

    def InitUI(self, parent):
        self.text_name = wx.StaticText(self, label='Device: \n\n', pos=(20,20))
        self.text_name.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.battery_level = wx.StaticText(self, label='Battery: \n\n', pos=(260,20))
        self.battery_level.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        # if the device is connected, the text_name label with the name of the device
        # and the battery_level label with the percentage of the battery left
        if parent.connected == True:
            name, battery = parent.listener.get()
            self.text_name.SetLabel(self.text_name.GetLabel() + name)
            self.battery_level.SetLabel(self.battery_level.GetLabel() + str(battery) + "%")
        # if the device is not connected, it inserts the "Connect" button to allows a new connection to the device
        else:
            connect_button = wx.Button(self, label="Connect", pos=(140,140))
            connect_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onConnectMenu(event, self))

        im = wx.Image('images/myo.png', wx.BITMAP_TYPE_ANY)
        im.Rescale(120,120)
        image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im), pos=(115,10))

        st = wx.StaticLine(self, wx.ID_ANY, pos=(20,150), size=(300,2), style=wx.LI_HORIZONTAL)

        # makes a listdir of the folder in which the gestures are present and returns all the gestures present
        path = os.getcwd() + '\\Dataset'
        gesture = os.listdir(path)
        self.list_box = wx.ListBox(self, pos=(25,180), size=(200, 180), choices=gesture)

        new_button = wx.Button(self, wx.ID_ANY, 'Add\n gesture', size=(90, 35), pos=(240,180))
        new_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onAddGesture(event, self))

        acquisition_button = wx.Button(self, wx.ID_ANY, 'Add\n acquisition', size=(90, 35), pos=(240,225))
        acquisition_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: self.onAddAcquisition(event, parent))

        rename_button = wx.Button(self, wx.ID_ANY, 'Rename', size=(90, 35), pos=(240,270))
        rename_button.Bind(wx.EVT_BUTTON, self.renameItem)

        delete_button = wx.Button(self, wx.ID_ANY, 'Delete', size=(90, 35), pos=(240,315))
        delete_button.Bind(wx.EVT_BUTTON, self.deleteItem)

        back_button= wx.Button(self, label='Back', pos=(20,410))
        back_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onBack(event, self))

        close_button = wx.Button(self, label='Close', pos=(250,410))
        close_button.Bind(wx.EVT_BUTTON, parent.onClose)



    # allows you to choose a gesture from those listed and go make new acquisitions for that gesture
    def onAddAcquisition(self, e, parent):
        sel = self.list_box.GetSelection()
        if sel == -1:
            wx.MessageBox("First select a gesture", "Info", wx.OK|wx.ICON_INFORMATION)
        text = self.list_box.GetString(sel)
        parent.onAddAcquisition(e=e, gesture=text, parent=self)


    # allows you to rename a gesture from those listed
    def renameItem(self, e):
        sel = self.list_box.GetSelection()
        if sel == -1:
            wx.MessageBox("First select a gesture", "Info", wx.OK|wx.ICON_INFORMATION)
        
        text = self.list_box.GetString(sel)
        renamed = wx.GetTextFromUser("Rename gesture", "Rename", text)

        if renamed != '':
            path = os.getcwd() + '\\Dataset\\'
            try:
                os.rename(path + text, path + renamed)
                self.list_box.Delete(sel)
                item_id = self.list_box.Insert(renamed, sel)
                self.list_box.SetSelection(item_id)
            except OSError:
                wx.MessageBox("Error during gesture renaming", "Info", wx.OK|wx.ICON_INFORMATION)


    # allows you to delete a gesture from those listed
    # involves deleting the gesture folder from the file system, with all the files inside it
    def deleteItem(self, e):
        sel = self.list_box.GetSelection()
        if sel == -1:
            wx.MessageBox("First select a gesture", "Info", wx.OK|wx.ICON_INFORMATION)
        text = self.list_box.GetString(sel)
        path = os.getcwd() + '\\Dataset\\' + text
        try:
            shutil.rmtree(path)
            self.list_box.Delete(sel)
        except OSError:
            wx.MessageBox("Error during gesture cancellation", "Info", wx.OK|wx.ICON_INFORMATION)




# panel that is activated if you choose "Training Model" from the Main Menu
# TODO the ability to train the model is not yet implemented
class Training(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
    
        self.InitUI(parent)

    
    def InitUI(self, parent):
        self.text_name = wx.StaticText(self, label='Device: \n\n', pos=(20,20))
        self.text_name.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.battery_level = wx.StaticText(self, label='Battery: \n\n', pos=(260,20))
        self.battery_level.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        # if the device is connected, the text_name label with the name of the device
        # and the battery_level label with the percentage of the battery left
        if parent.connected == True:
            name, battery = parent.listener.get()
            self.text_name.SetLabel(self.text_name.GetLabel() + name)
            self.battery_level.SetLabel(self.battery_level.GetLabel() + str(battery) + "%")
        # if the device is not connected, it inserts the "Connect" button to allows a new connection to the device
        else:
            connect_button = wx.Button(self, label="Connect", pos=(140,140))
            connect_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onConnectMenu(event, self))

        im = wx.Image('images/myo.png', wx.BITMAP_TYPE_ANY)
        im.Rescale(120,120)
        image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im), pos=(115,10))

        st = wx.StaticLine(self, wx.ID_ANY, pos=(20,150), size=(300,2), style=wx.LI_HORIZONTAL)

        text = wx.StaticText(self, label='Choose the model file', pos=(90,180))        
        self.choose_file = wx.FilePickerCtrl(self, message="Choose the file:", pos=(20,200), size=(300,40))

        upload_file = wx.Button(self, label='Upload', pos=(135,240))
        upload_file.Bind(wx.EVT_BUTTON, self.onUpload)

        back_button = wx.Button(self, label='Back', pos=(20,410))
        back_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onBack(event, self))

        close_button = wx.Button(self, label='Close', pos=(250,410))
        close_button.Bind(wx.EVT_BUTTON, parent.onClose)


    # it starts when "Upload" is pressed to upload the file with model
    def onUpload(self, e):
        print(self.choose_file.GetPath())



# panel that is activated if you choose "Testing Model" from the Main Menu
class Testing(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        self.InitUI(parent)
        

    def InitUI(self, parent):
        self.text_name = wx.StaticText(self, label='Device: \n\n', pos=(20,20))
        self.text_name.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.battery_level = wx.StaticText(self, label='Battery: \n\n', pos=(260,20))
        self.battery_level.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        name, battery = parent.listener.get()
        self.text_name.SetLabel(self.text_name.GetLabel() + name)
        self.battery_level.SetLabel(self.battery_level.GetLabel() + str(battery) + "%")

        im = wx.Image('images/myo.png', wx.BITMAP_TYPE_ANY)
        im.Rescale(120,120)
        image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im), pos=(115,10))

        st = wx.StaticLine(self, wx.ID_ANY, pos=(20,150), size=(300,2), style=wx.LI_HORIZONTAL)
        
        text = wx.StaticText(self, label='Choose the model file', pos=(90,180))        
        self.choose_file = wx.FilePickerCtrl(self, message="Choose the model file:", pos=(20,200), size=(300,40))

        text1 = wx.StaticText(self, label='Choose the weight file', pos=(90,260))        
        self.choose_file1 = wx.FilePickerCtrl(self, message="Choose the weight file:", pos=(20,280), size=(300,40))

        self.upload_file = wx.Button(self, label='Upload', pos=(135,340))
        self.upload_file.Bind(wx.EVT_BUTTON, lambda event, parent=parent: self.onUpload(event, parent))
        self.upload_file.Disable()

        # thread that ckecks if model architecture file and weights file have been upload
        self.check_insert = Thread(target=self.checkInsert)
        self.check_insert.start()
            
        back_button= wx.Button(self, label='Back', pos=(20,410))
        back_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onBack(event, self))

        close_button = wx.Button(self, label='Close', pos=(250,410))
        close_button.Bind(wx.EVT_BUTTON, parent.onClose)


    # thread that controls whether the architecture and weight files have been loaded
    # in case they are both loaded, enable the button to upload the files in the directory
    def checkInsert(self):
        while True:
            if self.choose_file.GetPath() != '' and self.choose_file1.GetPath() != '':
                self.upload_file.Enable()
                break
        

    # it start when "Upload" is pressed to upload files in directory
    # loading is done in the "NeuralNetwork" folder set up when the application starts
    def onUpload(self, e, parent):
        # check if the model and weight files are already in the NeuralNetwork directory
        # otherwise upload them to the NeuralNetwork folder
        path1 = os.getcwd() + '\\NeuralNetwork\\' + os.path.basename(self.choose_file.GetPath())
        if not os.path.exists(path1):
            shutil.copyfile(self.choose_file.GetPath(), path1)
        path2 = os.getcwd() + '\\NeuralNetwork\\' + os.path.basename(self.choose_file1.GetPath())
        if not os.path.exists(path2):
            shutil.copyfile(self.choose_file1.GetPath(), path2)
        parent.onPredict(e=e, parent=self, model=path1, weight=path2)



# panel that is activated when you want to make an acquisition in "Testing Model"
class Prediction(wx.Panel):

    count_emg = 0 # counter used to check if acquisitions of emg have ended
    count_imu = 0 # counter used to check if acquisitions of imu have ended
    duration_ms = 2000 # duration of acquisition in milliseconds
    freq_emg = 200 # emg acquisition frequency
    freq_imu = 200 # imu acquisition frequency


    def __init__(self, parent, model, weight):
        wx.Panel.__init__(self, parent=parent)

        self.emg = []
        self.imu = []

        self.InitUI(parent, model, weight)
        
        with open(model,'r') as f:
            modell = json.load(f)
        
        modell1 = json.dumps(modell)

        self.classificator = model_from_json(modell1) # upload architecture model
        self.classificator.load_weights(weight) # upload weights


    def InitUI(self, parent, model, weight):
        self.text_name = wx.StaticText(self, label='Device: \n\n', pos=(20,20))
        self.text_name.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.battery_level = wx.StaticText(self, label='Battery: \n\n', pos=(260,20))
        self.battery_level.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        name, battery = parent.listener.get()
        self.text_name.SetLabel(self.text_name.GetLabel() + name)
        self.battery_level.SetLabel(self.battery_level.GetLabel() + str(battery) + "%")

        im = wx.Image('images/myo.png', wx.BITMAP_TYPE_ANY)
        im.Rescale(120,120)
        image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im), pos=(115,10))

        st = wx.StaticLine(self, wx.ID_ANY, pos=(20,150), size=(300,2), style=wx.LI_HORIZONTAL)

        t = wx.StaticText(self, label='Run a gesture and I will try to guess it', pos=(35,200))
        t.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        self.start_button = wx.Button(self, label='Start', pos=(135,260))
        self.start_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent, model=model, weight=weight: self.onStart(event, parent, model, weight))

        self.progress_bar = wx.Gauge(self, range=100, pos=(45,300), size=(250,25), style=wx.GA_HORIZONTAL) 

        back_button= wx.Button(self, label='Back', pos=(20,410))
        back_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onBack(event, self))

        close_button = wx.Button(self, label='Close', pos=(250,410))
        close_button.Bind(wx.EVT_BUTTON, parent.onClose)


    # it starts when "Start" is pressed
    def onStart(self, e, parent, model, weight):
        self.start_button.Disable()

        # start acquisition
        self.startAcquisition(parent)

        self.count_emg = int((self.duration_ms / 1000) * self.freq_emg)
        self.count_imu = int((self.duration_ms / 1000) * self.freq_imu)

        # check acquisition end
        self.check_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event, parent=parent, model=model, weight=weight: self.checkAcquisition(event, parent, model, weight), self.check_timer)
        self.check_timer.Start(100)


    # check the termination of the acquisition throught the use of a timer that every 100 ms
    # go to check if the current lenght of the acquisition is equal to the necessary one
    # when the required lenght is reached, the timer is blocked
    def checkAcquisition(self, e, parent, model, weight):
        # if all emg and imu acquisition have been made
        # the number of acquisition is calculated as acquisitions' duration by acquisitions' frequency
        if (len(self.emg) == ( (self.duration_ms / 1000) * self.freq_emg) ) and (len(self.imu) == ( (self.duration_ms / 1000) * self.freq_imu) ):
            self.endAcquisition(e=e, parent=parent, model=model, weight=weight)
            self.check_timer.Stop()
    

    # it starts one the established acquisitions are reached
    # activate the predict and then call the function to activate the panel showing the predicted gesture
    def endAcquisition(self, e, parent, model, weight):
        prediction = self.predictGesture()
        parent.onResult(e=e, parent=self, prediction=prediction, model=model, weight=weight)


    # is the function that activates the predict
    # create the data to predict first, taking the acquisition made first
    # then permorm the predict and return the predicted gesture
    def predictGesture(self):
        data = self.createArray()

        # pass the correct dimension to the neural network
        data = np.reshape(data, (1, data.shape[0], data.shape[1]))
        prediction = self.classificator.predict(data)
        predicted_class = np.argmax(prediction)
        label = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
        predicted_label = label[predicted_class]
        return predicted_label


    # creates the data to be passed to the predict, taking the values ​​from the self.emg and self.imu which contain the acquisition just made
    def createArray(self):
        x1 = []
        gyr = []
        acc = []
        ori = []
        emg = []


        nr_samples = int(self.duration_ms / 1000 * int(self.freq_emg))
        for k in range(0, nr_samples):
            emg.append(self.emg[k])
            
        imu = self.imu
        for m in imu:
            gyr.append(m["gyroscope"])
            acc.append(m["acceleration"])
            ori.append(m["orientation"])

        for i in range(0, len(emg)):
            x = [emg[i], gyr[i], acc[i], ori[i]]

            flat = []
            for sublist in x:
                for item in sublist:
                    flat.append(item)

            x1.append(flat)

        x2 = np.array(x1)
        return x2
    

    # decreases the emg counter in which there is the number of acquisitions still to be made
    def decreaseEmgCount(self):
        self.count_emg = self.count_emg - 1
        if self.count_emg == 0:
            self.emg_timer.Stop()


    # decreases the imu counter in which there is the number of acquisitions still to be made
    def decreaseImuCount(self):
        self.count_imu = self.count_imu - 1
        if self.count_imu == 0:
            self.imu_timer.Stop() 


    # activates 2 timers, which periodically perform acquisitions for emg and imu
    def startAcquisition(self, parent):
        self.emg.clear()
        self.imu.clear()

        self.emg_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event, parent=parent: self.acquireEmg(event, parent), self.emg_timer)
        self.emg_timer.Start(1000 / self.freq_emg)

        self.imu_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event, parent=parent: self.acquireImu(event, parent), self.imu_timer)
        self.imu_timer.Start(1000 / self.freq_imu)

    
    # acquires emg signals by fetching them through the listener
    def acquireEmg(self, e, parent):
        self.emg.append(parent.listener.emg)

        # modify the progress bar
        perc = int(len(self.emg) * 100 / ((self.duration_ms / 1000) * self.freq_emg))
        self.progress_bar.SetValue(perc)

        self.decreaseEmgCount()


    # acquires imu signals by fetching them through the listener
    def acquireImu(self, e, parent):
        self.imu.append(parent.listener.data)
        self.decreaseImuCount()




# panel where the predict result is shown
class Result(wx.Panel):

    def __init__(self, parent, prediction, model, weight):
        wx.Panel.__init__(self, parent=parent)

        self.InitUI(parent, prediction, model, weight)

    
    def InitUI(self, parent, prediction, model, weight):
        self.text_name = wx.StaticText(self, label='Device: \n\n', pos=(20,20))
        self.text_name.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.battery_level = wx.StaticText(self, label='Battery: \n\n', pos=(260,20))
        self.battery_level.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        name, battery = parent.listener.get()
        self.text_name.SetLabel(self.text_name.GetLabel() + name)
        self.battery_level.SetLabel(self.battery_level.GetLabel() + str(battery) + "%")

        im = wx.Image('images/myo.png', wx.BITMAP_TYPE_ANY)
        im.Rescale(120,120)
        image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im), pos=(115,10))

        st = wx.StaticLine(self, wx.ID_ANY, pos=(20,150), size=(300,2), style=wx.LI_HORIZONTAL)

        t = wx.StaticText(self, label='Did I guess?', pos=(120,170))
        t.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        im1 = wx.Image('images/' + str(prediction) + '.jpg', wx.BITMAP_TYPE_ANY)
        im1.Rescale(160,160)
        image1 = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im1), pos=(90,200))

        tryagain_button = wx.Button(self, label='Try again', pos=(135,380))
        tryagain_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent, model=model, weight=weight: parent.onRestart(event, self, model, weight))

        back_button= wx.Button(self, label='Back', pos=(20,410))
        back_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onBack(event, self))

        close_button = wx.Button(self, label='Close', pos=(250,410))
        close_button.Bind(wx.EVT_BUTTON, parent.onClose)





# panello to make acquisitions
class Acquisition(wx.Panel):

    count_emg = 0 # counter used to check if acquisitions of emg have ended
    count_imu = 0 # counter used to check if acquisitions of imu have ended
    duration_ms = 2000 # duration of acquisition in milliseconds
    freq_emg = 200 # emg acquisition frequency
    freq_imu = 200 # imu acquisition frequency


    def __init__(self, parent, gesture_name):
        wx.Panel.__init__(self, parent=parent)

        self.emg = []
        self.imu = []

        count = self.getAcquisitionNumber(gesture_name)

        self.InitUI(parent, gesture_name, count)


    def InitUI(self, parent, gesture_name, count):        
        self.text_name = wx.StaticText(self, label='Device: \n\n', pos=(20,20))
        self.text_name.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        self.battery_level = wx.StaticText(self, label='Battery: \n\n', pos=(260,20))
        self.battery_level.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        name, battery = parent.listener.get()
        self.text_name.SetLabel(self.text_name.GetLabel() + name)
        self.battery_level.SetLabel(self.battery_level.GetLabel() + str(battery) + "%")
        
        im = wx.Image('images/myo.png', wx.BITMAP_TYPE_ANY)
        im.Rescale(120,120)
        image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(im), pos=(115,10))

        st = wx.StaticLine(self, wx.ID_ANY, pos=(20,150), size=(300,2), style=wx.LI_HORIZONTAL)

        t = wx.StaticText(self, label='Start acquisition for gesture: ', pos=(60,200))
        t.SetLabel(t.GetLabel() + gesture_name)
        t.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        t1 = wx.StaticText(self, label='Press "Start" and perform gesture', pos=(80, 230))

        self.start_button = wx.Button(self, label='Start', pos=(135,260))
        self.start_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: self.onStart(event, parent))

        self.progress_bar = wx.Gauge(self, range=100, pos=(45,300), size=(250,25), style=wx.GA_HORIZONTAL) 
        
        self.conf_button = wx.Button(self, label='Save', pos=(20,340))
        self.conf_button.Bind(wx.EVT_BUTTON, lambda event, gesture=gesture_name, parent=parent: self.onConf(event, gesture_name, parent))
        self.conf_button.Disable()

        t2 = wx.StaticText(self, label='     Total\nacquisition:\n         ', pos=(140,340))
        t2.SetLabel(t2.GetLabel() + str(count))
        t2.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        self.delete_button = wx.Button(self, label='Delete', pos=(260,340))
        self.delete_button.Bind(wx.EVT_BUTTON, lambda event, sender=self, gesture=gesture_name: parent.reAcquisition(event, self, gesture_name))
        self.delete_button.Disable()

        back_button = wx.Button(self, label='Back', pos=(20,410))
        back_button.Bind(wx.EVT_BUTTON, lambda event, parent=parent: parent.onBack(event, self))

        close_button = wx.Button(self, label='Close', pos=(250,410))
        close_button.Bind(wx.EVT_BUTTON, parent.onClose)



    # returns the number of acquisitons made for a specific gesture
    # consist on make a listdir on the gesture directory
    def getAcquisitionNumber(self, gesture):
        path = os.getcwd() + '\\Dataset\\' + gesture
        return len(os.listdir(path))

    
    # it starts when "Start" is pressed
    # inizialize emg and imu acquisitions
    # it also activates a timer that periodically checks whether the acquisitions for emg and imu have ended
    def onStart(self, e, parent):
        self.start_button.Disable()

        # start acquisitions
        self.startAcquisition(parent)

        self.count_emg = int((self.duration_ms / 1000) * self.freq_emg)
        self.count_imu = int((self.duration_ms / 1000) * self.freq_imu)

        # check acquisitions end
        self.check_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.checkAcquisition, self.check_timer)
        self.check_timer.Start(100)
        

    # check the termination of the acquisition throught the use of a timer that every 100 ms
    # go to check if the current lenght of the acquisition is equal to the necessary one
    # when the required lenght is reached, the timer is blocked
    def checkAcquisition(self, e):
        # if all emg and imu acquisition have been made
        # the number of acquisition is calculated as acquisitions' duration by acquisitions' frequency
        if (len(self.emg) == ( (self.duration_ms / 1000) * self.freq_emg) ) and (len(self.imu) == ( (self.duration_ms / 1000) * self.freq_imu) ):
            self.endAcquisition()
            self.check_timer.Stop()

    
    # it consists in enabling the buttons to save or cancel the acquisition just made
    def endAcquisition(self):
        self.conf_button.Enable()
        self.delete_button.Enable()


    # decreases the emg counter in which there is the number of acquisitions still to be made
    def decreaseEmgCount(self):
        self.count_emg = self.count_emg - 1
        if self.count_emg == 0:
            self.emg_timer.Stop()


    # decreases the imu counter in which there is the number of acquisitions still to be made
    def decreaseImuCount(self):
        self.count_imu = self.count_imu - 1
        if self.count_imu == 0:
            self.imu_timer.Stop() 


    # activates 2 timers, which periodically perform acquisitions for emg and imu
    def startAcquisition(self, parent):
        self.emg.clear()
        self.imu.clear()

        self.emg_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event, parent=parent: self.acquireEmg(event, parent), self.emg_timer)
        self.emg_timer.Start(1000 / self.freq_emg)

        self.imu_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event, parent=parent: self.acquireImu(event, parent), self.imu_timer)
        self.imu_timer.Start(1000 / self.freq_imu)

    
    # acquires emg signals by fetching them through the listener
    def acquireEmg(self, e, parent):
        self.emg.append(parent.listener.emg)

        # modify the progress bar
        perc = int(len(self.emg) * 100 / ((self.duration_ms / 1000) * self.freq_emg))
        self.progress_bar.SetValue(perc)

        self.decreaseEmgCount()


    # acquires imu signals by fetching them through the listener
    def acquireImu(self, e, parent):
        self.imu.append(parent.listener.data)
        self.decreaseImuCount()


    # if "Save" is pressed for the acquisition just made, the structure is created to save the file
    # the the file is saved in json format
    # at the end the panel is reload, giving the possibility to make a new acquisition
    def onConf(self, e, gesture_name, parent):
        # composition of output file
        data = {
            "timestamp": datetime.datetime.now().strftime("%d/%m/%y/%H:%M:%S"),
            "duration": self.duration_ms,
            "emg": {
                "frequency": self.freq_emg,
                "data": self.emg
            },
            "imu": {
                "frequency": self.freq_imu,
                "data": self.imu
            }
        }

        file_name = str(uuid.uuid4()) # create random uuid
        path_file = os.getcwd() + '\\Dataset\\' + gesture_name + '\\' + file_name + '.json'
        try:
            with open(path_file, 'w') as f:
                json.dump(data, f)
            wx.MessageBox("Acquisition saved successfully!", "Info", wx.OK|wx.ICON_INFORMATION)
        except OSError:
            wx.MessageBox("Error during acquisition saving, please try again with another acquisition", "Info", wx.OK|wx.ICON_INFORMATION)

        parent.reAcquisition(e=e, sender=self, gesture=gesture_name)






if __name__ == '__main__':
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    app.MainLoop()

    