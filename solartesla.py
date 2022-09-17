import requests
import json
import time
from datetime import datetime
from datetime import timedelta
import math
import hashlib

# Required python packages:
# pip3 install TeslaPy
# pip3 install selenium

# When using on the Raspberry Pi please install:
# sudo apt-get install chromium-chromedriver

# -----

# TTD: How to prevent the app from stop charging when at another location?
# Save the cars location by 3 decimal points -> around 12 meters accurate.

# TTD: When updating your Tesla; the SolarTesla app crashes

# Uses: https://github.com/tdorssers/TeslaPy
import teslapy

from tkinter import *

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait



# Settings filename
sFileName = 'settings.st'
mincurrent = -25000
iCurrentChargeRate = 0
TeslaChargingSpeedWatt = 0
TeslaCharging = "Not set"
sSimulatedStatus = ""
bActive = True
sStatus = "disconnected"
sValue = 0
TeslaBattery = 0
dLastRateChange = datetime.now()

# Subtract 16 minutes to start first update directly on start-up
dLastOnOff = datetime.now()
dLastOnOff = dLastOnOff - timedelta(minutes=16)

# Start GUI
root = Tk()
root.geometry('450x300')
root.title('SolarTesla')

# Get settings from file
def GetSettings():
    global jSettings
    try:
        fFile = open(sFileName, 'r')
        jSettings = json.load(fFile)
        fFile.close()
    except IOError:
        # Default settings (json format)
        jSettings = {'HomeWizardIp': '192.168.1.254', 'UserEmail': 'your@mail.com', 'MinChargingTime': 300}
        SaveSettings()
    
    
# Save settings to file
def SaveSettings():
    with open(sFileName, 'w') as json_file:
        json.dump(jSettings, json_file)

# Search for HomeWizard IP address automaticly (assumed on 192.168.1.x)
def CheckHomeWizard():
    global HomeWizardIp
    for ip in range(2, 255): # range(2, 255)
        lblSimulateStatus = Label(root, text="Searching HomeWizard: 192.168.1."+str(ip)+"        ")
        lblSimulateStatus.grid(row=9, column=1, sticky='w')
        try:
            resp = requests.get(f"http://192.168.1.%d/api/v1/data" % ip, verify=False, timeout=1)

            if resp.status_code == 200:
                # 200 terug; controleer of het de HomeWizard is
                if str(abs(resp.json()['active_power_w'])).isnumeric():
                    lblSimulateStatus = Label(root, text="Found HomeWizard: 192.168.1."+str(ip)+"        ")
                    lblSimulateStatus.grid(row=9, column=1, sticky='w')                    
                    #print("HomeWizard found at 192.168.1."+str(ip))
                    HomeWizardIp = '192.168.1.'+str(ip)
                    jSettings['HomeWizardIp'] = HomeWizardIp
                    SaveSettings()
                    break
        except:
            pass
            


GetSettings()
HomeWizardIp = jSettings['HomeWizardIp']
UserEmail = jSettings['UserEmail']
MinChargingTime = jSettings['MinChargingTime']

# Maak een hash van het e-mailadres als userid op de SolarTesla site
hash_object = hashlib.sha1(UserEmail.encode('utf-8'))
hex_dig = hash_object.hexdigest()


def custom_auth(url):
    with webdriver.Chrome() as browser:
        browser.get(url)
        WebDriverWait(browser, 300).until(EC.url_contains('void/callback'))
        return browser.current_url

with teslapy.Tesla(UserEmail, authenticator=custom_auth) as tesla:
    tesla.fetch_token()



def CheckStatus():
    if bActive:
        try:
            response = requests.get("http://"+HomeWizardIp+"/api/v1/data", verify=False, timeout=4)      
            current = str(response.json()['active_power_w'])
            global iCurrent
            icurrent = current
            # rood of groen tonen van wattage
            if int(icurrent) > 0:
                sColor = "indianred"
            else:
                sColor = "forestgreen"
        
            # Minimaal beschikbare stroom in de laatste 60 seconden bijhouden
            global mincurrent
            if int(icurrent) > 0:
                mincurrent = 0
            elif int(icurrent) > int(mincurrent):
                mincurrent = icurrent
            else:
                mincurrent = int(mincurrent) - 10
        

            # Format number with dots for thousands
            current = "{:,}".format(int(current)).replace(',','.')
    
            # Update label
            myLabel2 = Label(root, text=current+" w (MIN: "+str(mincurrent)+")      ", fg=sColor)
            myLabel2.grid(row=1, column=1, sticky='w')
     
            UpdateCharging(mincurrent)
        
            # Keep refreshing every second
            root.after(1000, CheckStatus)

        except:    
            # HomeWizard P1 meter not found; search
            CheckHomeWizard()
            
    else:
        myLabel2 = Label(root, text="Sleeping         ", fg="black")
        myLabel2.grid(row=1, column=1, sticky='w')
            
        # Keep refreshing minute
        root.after(1000, CheckStatus)

    # Laadsnelheid aanpassen
    #vehicles[0].command('CHARGING_AMPS', charging_amps=16)
    # Laden starten
    #vehicles[0].command('START_CHARGE')
    # Laden stoppen
    #vehicles[0].command('STOP_CHARGE')

def TeslaInfo():
    global TeslaCharging
    global TeslaBattery
    
    if bActive:

        try:    
            with teslapy.Tesla(UserEmail) as tesla:
                vehicles = tesla.vehicle_list()
                vehicles[0].sync_wake_up()
        
                TeslaName = vehicles[0].get_vehicle_data()['display_name']
                TeslaBattery = vehicles[0].get_vehicle_data()['charge_state']['battery_level']
                TeslaCharging = vehicles[0].get_vehicle_data()['charge_state']['charging_state']
                TeslaChargingSpeed = vehicles[0].get_vehicle_data()['charge_state']['charge_current_request']
                TeslaChargingRate = vehicles[0].get_vehicle_data()['charge_state']['charge_rate']
            
                TeslaPort = vehicles[0].get_vehicle_data()['drive_state']['latitude']
                TeslaPort = str(TeslaPort) + ", "
                TeslaPort = TeslaPort + str(vehicles[0].get_vehicle_data()['drive_state']['longitude'])
                
            myLabel4 = Label(root, text=TeslaName)
            myLabel4.grid(row=3, column=1, sticky='w')

            myLabel6 = Label(root, text=str(TeslaBattery)+" %")
            myLabel6.grid(row=4, column=1, sticky='w')

            myLabel6 = Label(root, text=TeslaCharging)
            myLabel6.grid(row=5, column=1, sticky='w')                
                
        except:
            lblWebconnectStatus = Label(root, text="Could not connect to your Tesla.         ")
            lblWebconnectStatus.grid(row=10, column=1, sticky='w')


        if TeslaCharging != 'Disconnected':
            myLabel10 = Label(root, text=TeslaPort)
            myLabel10.grid(row=6, column=1, sticky='w')
    
            global TeslaChargingSpeedWatt
            TeslaChargingSpeedWatt = TeslaChargingSpeed * 240 * 3
            TeslaChargingSpeedWattDisplay = "{:,}".format(int(TeslaChargingSpeedWatt)).replace(',','.')
            TeslaChargingSpeedInfo = str(TeslaChargingSpeed) + " A (" + TeslaChargingSpeedWattDisplay + " W)     "
            lblChargeRate = Label(root, text=TeslaChargingSpeedInfo)
            lblChargeRate.grid(row=7, column=1, sticky='w')
        
    
    # Get info again after 15 minutes (in milliseconds)
    root.after(900000, TeslaInfo)

    #print(vehicles[0].get_vehicle_data()['charge_state']['battery_level'])
    #print(vehicles[0].get_vehicle_data()['charge_state']['charge_current_request'])
    #print(vehicles[0].get_vehicle_data()['charge_state']['charge_current_request_max'])
    #print(vehicles[0].get_vehicle_data()['charge_state']['charging_state'])
    #print(vehicles[0].get_vehicle_data()['charge_state']['charge_limit_soc'])
    #print(vehicles[0].get_vehicle_data()['charge_state']['charging_state'])

def StartCharging():     
    global iCurrentChargeRate
    global TeslaCharging
    lblSimulateStatus = Label(root, text="Start charging called ("+TeslaCharging+")          ")
    lblSimulateStatus.grid(row=9, column=1, sticky='w')     
    if TeslaCharging == 'Stopped': 
        with teslapy.Tesla(UserEmail) as tesla:
            #Laad to maximaal 90% (moet nog setting worden)
            if int(TeslaBattery) < 90:
                vehicles = tesla.vehicle_list()
                vehicles[0].sync_wake_up()
                vehicles[0].command('START_CHARGE')

                iCurrentChargeRate = frmChargingRate.get()
                if not iCurrentChargeRate:
                    iCurrentChargeRate == 5

                iCurrentChargeRate = int(iCurrentChargeRate)*240*3
                time.sleep(2)
                TeslaInfo()
                lblSimulateStatus = Label(root, text="Charging with "+str(iCurrentChargeRate)+" W       ")
                lblSimulateStatus.grid(row=9, column=1, sticky='w')
            else:
                lblSimulateStatus = Label(root, text="Charge limit reached            ")
                lblSimulateStatus.grid(row=9, column=1, sticky='w')
    else:
        time.sleep(3)
        TeslaInfo()        
        

def StopCharging():
    with teslapy.Tesla(UserEmail) as tesla:
        vehicles = tesla.vehicle_list()
        vehicles[0].sync_wake_up()
        vehicles[0].command('STOP_CHARGE')
        global iCurrentChargeRate
        iCurrentChargeRate = 0
        time.sleep(1)
        TeslaInfo()
        lblSimulateStatus = Label(root, text="Charging stopped       ")
        lblSimulateStatus.grid(row=9, column=1, sticky='w')

def UpdateChargeRate():
    with teslapy.Tesla(UserEmail) as tesla:
        vehicles = tesla.vehicle_list()
        vehicles[0].sync_wake_up()
        vehicles[0].command('CHARGING_AMPS', charging_amps=frmChargingRate.get())
        time.sleep(1)
        TeslaInfo()
    
# Web interface; enables putting the app to sleep via a webpage (for instance on your smartphone) and status updates    
def ConnectSolarTesla():
    global sStatus    
    global bActive
    global TeslaCharging

    if sStatus == 'sleep':
        TeslaCharging = 'sleep'

    if sValue is None:
        sValue == 0

    if TeslaBattery is None:
        TeslaBattery == 0
        
    if TeslaCharging is None:
        TeslaCharging == 'error'
        

    url = 'https://solartesla.nl/api/connect.asp?u='+hex_dig+'&s='+TeslaCharging+'&e='+UserEmail+'&v='+str(sValue)+'&soc='+str(TeslaBattery)
    try: 
        reply = requests.get(url)
        lblWebconnectStatus = Label(root, text=reply.text+", s="+TeslaCharging+", v="+str(sValue)+", soc="+str(TeslaBattery)+"       ")
        lblWebconnectStatus.grid(row=10, column=1, sticky='w')
    
        #Verwerk de reply
        if reply.text == 'sleep':
            #Zet de app in slaapmodus;
            bActive = False
            sStatus = 'sleep'
        elif reply.text == 'awake':
            bActive = True
            sStatus = 'disconnected'        
    except:
        lblWebconnectStatus = Label(root, text="Unable to connect to SolarTesla server.")
        lblWebconnectStatus.grid(row=10, column=1, sticky='w')
        
    # Get info again after 1 minute (in milliseconds - 60000)
    root.after(60000, ConnectSolarTesla)
        

# functie die kijkt of er geladen moet worden. 
def UpdateCharging(mincurrent):
    # Check of er stroomoverschot is en bepaal de juiste laadsnelheid (elke ampare = 240 Watt * 3 fases)
    global iChargeRate
    global dLastRateChange
    global dLastOnOff
    global sValue
    global sStatus
                   
    # Check of de auto in de oplader zit
    if TeslaCharging != 'Disconnected':
                
        #Huidige laadsnelheid = TeslaChargingSpeedWatt
        CurrentRate = math.floor(abs(int(TeslaChargingSpeedWatt))/240/3)       
        #Huidige apperage
        iChargeRate = math.floor((int(TeslaChargingSpeedWatt)+abs(int(mincurrent)))/240/3)


        if TeslaCharging == "Charging":
           #De auto is aan het laden 

            #Kijk eerst hoe lang het geleden is dat de laadsnelheid aangepast is
            #Hier moet altijd wat tijd tussenzitten.
            dTime = datetime.now()
            dDelta = dTime - dLastRateChange

            lblSimulateStatus = Label(root, text="dif: "+str(dDelta.total_seconds())+"   ")
            lblSimulateStatus.grid(row=9, column=1, sticky='w')  
    
            if int(iChargeRate) > 16:
                iChargeRate = 16
     
            frmChargingRate.delete(0, END) # Deletes the current value
            frmChargingRate.insert(0, iChargeRate) # inserts new value     

            if int(dDelta.total_seconds()) > 60:
                #reset teller
                dLastRateChange = datetime.now()                   
                
                if abs(int(mincurrent)) < 1:
                    iChargeRate = iChargeRate - 1
                    frmChargingRate.delete(0, END) # Deletes the current value
                    frmChargingRate.insert(0, iChargeRate) # inserts new value
                
        
                if int(iChargeRate) > 0:
                    #Alleen updaten als er ook daadwerkelijk iets verandert
                    if int(CurrentRate) != int(iChargeRate):
                        UpdateChargeRate()
                        sStatus = "charging"
                        sValue = iChargeRate
                elif int(iChargeRate) == 0:
                    #Te weinig stroom beschikbaar; uitschakelen
                    dTime = datetime.now()
                    dDelta2 = dTime - dLastOnOff
                    
                    #Zet alleen aan als de laatste keer uitzetten meer dan 10 minuten geleden is
                    if int(dDelta2.total_seconds()) > 600:
                        #reset teller
                        dLastOnOff = datetime.now()
                        StopCharging()
                
        else:
            #De auto is niet aan het laden; kijk of ie aangezet moet worden
            dTime = datetime.now()
            dDelta3 = dTime - dLastOnOff
    
            #lblSimulateStatus = Label(root, text="test3: "+str(dDelta3.total_seconds())+" | " + str(iChargeRate) + "   ")
            #lblSimulateStatus.grid(row=9, column=1, sticky='w')          
    
            #Kijk of er voldoende stroom over is om te starten met laden
            if int(iChargeRate) > 0:
    
                #Zet alleen aan als de laatste keer uitzetten meer dan 10 minuten geleden is
                if int(dDelta3.total_seconds()) > 600:
                    #reset teller
                    dLastOnOff = datetime.now()              
                    StartCharging()        
                    sStatus = "charging"
            
    # Check of de auto thuis is
    # Check of de auto in de oplader zit
    # Check of de auto al aan het laden is (update eventueel snelheid)
    

# Create text label widget
myHeader1 = Label(root, text="Your house", font="Helvetica 14 bold")
myLabel1 = Label(root, text="Current use: ")
myLabel2 = Label(root, text=" ")

myHeader2 = Label(root, text="Your Tesla", font="Helvetica 14 bold")
myLabel3 = Label(root, text="Connected to: ")
myLabel4 = Label(root, text="")
myLabel5 = Label(root, text="State of Charge: ")
myLabel6 = Label(root, text="")
myLabel7 = Label(root, text="Charge status: ")
myLabel8 = Label(root, text="")
myLabel9 = Label(root, text="Location: ")
myLabel10 = Label(root, text="")

btnStartCharging = Button(root, text="Start charging", padx=5, pady=5, command=StartCharging)
btnStopCharging = Button(root, text="Stop charging", padx=5, pady=5, command=StopCharging)
btnChangeRate = Button(root, text="adjust rate", padx=5, pady=5, command=UpdateChargeRate)
lblChargingRate = Label(root, text="Charge rate (5-16): ")
lblChargeRate = Label(root, text="")
frmChargingRate = Entry(root, width=3)

# Display
myHeader1.grid(row=0, column=0, sticky='w')
myLabel1.grid(row=1, column=0, sticky='w')
myLabel2.grid(row=1, column=1, sticky='w')

myHeader2.grid(row=2, column=0, sticky='w')
myLabel3.grid(row=3, column=0, sticky='w')
myLabel4.grid(row=3, column=1, sticky='w')
myLabel5.grid(row=4, column=0, sticky='w')
myLabel6.grid(row=4, column=1, sticky='w')
myLabel7.grid(row=5, column=0, sticky='w')
myLabel8.grid(row=5, column=1, sticky='w')
myLabel9.grid(row=6, column=0, sticky='w')
myLabel10.grid(row=6, column=1, sticky='w')

lblChargingRate.grid(row=7, column=0, sticky='w')
lblChargeRate.grid(row=7, column=1, sticky='w')
frmChargingRate.grid(row=7, column=2, sticky='w')
btnStartCharging.grid(row=8, column=0, sticky='w')
btnStopCharging.grid(row=8, column=1, sticky='w')
btnChangeRate.grid(row=8, column=2, sticky='w')

frmChargingRate.delete(0, END) # Deletes the current value
frmChargingRate.insert(0, 5) # inserts new value 

lblSimulate = Label(root, text="Simulated Status:")
lblSimulate.grid(row=9, column=0, sticky='w')
lblSimulateStatus = Label(root, text="")
lblSimulateStatus.grid(row=9, column=1, sticky='w')

lblWebconnect = Label(root, text="Connection:")
lblWebconnect.grid(row=10, column=0, sticky='w')
lblWebconnectStatus = Label(root, text="")
lblWebconnectStatus.grid(row=10, column=1, sticky='w')


# Get status HomeWizard
CheckStatus()

# Get Tesla status
TeslaInfo()

# Connect to the SolarTesla website server
ConnectSolarTesla()


root.mainloop()
