import requests
import time
from calibration import calibrate, get_data_from_api
import matplotlib.pyplot as plt
from dateutil import parser
from datetime import timedelta
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import linregress
from datetime import datetime
import seaborn as sns
import pytz

class exponential_decay():
    def __init__(self, start:datetime, stop:datetime, window_open:bool, coefs, locationId:str=80176):
        self.start = start.astimezone(pytz.utc)
        self.stop = stop.astimezone(pytz.utc)
        self.window_open = window_open
        self.duration = self.start - self.stop
        
        self.start_str = start.strftime("%Y%m%dT%H%M%SZ")
        self.stop_str = stop.strftime("%Y%m%dT%H%M%SZ")

        self.data_datetimes, self.data_dict = get_calibrated_past_data(locationId, coefs, self.start_str, self.stop_str)
        self.data_timedeltas = [(d - self.start).seconds/3600 for d in self.data_datetimes]

        self.rescaled_data = {}
        self.coefs = {}

    def __len__(self):
        return len(self.data_timedeltas)
    
    def rescale(self, rescale_index:int, species:str):
        popt, pcov = curve_fit(exponential_func, self.data_timedeltas, self.data_dict[species], p0=(500, -0.5, 400))
        self.coefs[species] = popt
        self.rescaled_data[species] = (self.data_dict[species] - popt[2]) / popt[0]

# Fit the function a * np.exp(b * t) + c to x and y
def exponential_func(t, a, b, c):
    return a * np.exp(b * t) + c

def get_current_data_from_api(id:str):
    auth_token = "f2aec323-a779-4ee1-b63f-d147612982fb"
    auth_string = f"?token={auth_token}"
    source_url = "https://api.airgradient.com/public/api/v1/"
    locationId = id

    endpoint = f"locations/{locationId}/measures/current"
    req_url = source_url + endpoint + auth_string
    response = requests.get(req_url).json()

    print(response)
    return response
def apply_calibration(coefs, data):
    if type(data) == int:
        return int(data * coefs[0] + coefs[1])
    else:
        return [int((d * coefs[0] + coefs[1])) for d in data]
def get_calibrated_past_data(id:str, coefs, t1:str, t2:str):
    response = get_data_from_api(id, t1, t2)

    data_dict = {}
    for label in response[0].keys():
        data_dict[label] = np.asarray([d[label] for d in response])


    data_dict["rco2"] = data_dict["rco2"] * coefs[0] + coefs[1]
    times = [parser.parse(d["timestamp"]) for d in response]

    data_dict["timedelta"] = [(t-times[0]).seconds/3600 for t in times]

    return times, data_dict
def get_live_data(id, coefs):
     while True:
        raw_data = get_current_data_from_api(id)
        co2_val = raw_data["rco2"] 
        adjusted_current_co2 = apply_calibration(coefs, co2_val)
        print(f"Raw reading: {co2_val}ppm, Calibrated: {adjusted_current_co2}ppm")
        time.sleep(60)
def exponentials_plots(locationId, coefs):
    t1 = "20241117T012000Z" # EXPONENT TIMES
    t2 = "20241117T082500Z"
    
    times, data_dict = get_calibrated_past_data(locationId, coefs, t1, t2) 
        
    fig, axs = plt.subplots(nrows=3, sharex=True)
   
    for ax, label, pretty in zip(axs, ["rco2", "tvoc", "pm10"], ["CO2 (ppm)", "TVOC (ppm)", "PM10 (ppm)"]):
        popt, pcov = curve_fit(exponential_func, data_dict["timedelta"], data_dict[label], p0=(1, -1e-5, 600))
        print(popt, pcov)
        ax.plot(data_dict["timedelta"], data_dict[label], label='Observed Data')
        ax.plot(data_dict["timedelta"], exponential_func(np.asarray(data_dict["timedelta"]), *popt), label='Fit: y = %5.0f * exp(%5.4f * x) + %5.0f' % tuple(popt))
        ax.legend()
        ax.set_ylabel(pretty)
        ax.text(0.75, 0.75, rf"$\tau = {-1/popt[1]:.2f}$ hours", transform=ax.transAxes)

    plt.suptitle("Exponential Decay of CO2 and TVOC in Poorly Ventilated Residential Kitchen") 
    plt.legend()
    plt.xlabel("Time (Hours)")
    fig.tight_layout()
    plt.show()

def simple_plot(times, data_dict):
    fig, axs = plt.subplots(nrows=3, sharex=True)
    axs[0].plot(times, data_dict["rco2"])
    axs[0].set_ylabel("Calibrated CO2 (ppm)")
    axs[1].plot(times, data_dict["tvoc"])
    axs[1].set_ylabel("tvoc (ppm)")
    axs[2].plot(times, data_dict["pm10"])
    axs[2].set_ylabel("pm10 (ppm)")
    fig.tight_layout()
    plt.show()
def initialise():
    locationId = "80176"    
    coefs = calibrate(locationId)

    t1 = "20241119T000000Z"
    t2 = "20241126T093000Z"
    times, data_dict = get_calibrated_past_data(locationId, coefs, t1, t2)    

    curves = []
    curves.append(exponential_decay(datetime(2024, 11, 19, 5, 45), datetime(2024, 11, 19, 10, 55), False, coefs))
    curves.append(exponential_decay(datetime(2024, 11, 20, 5, 45), datetime(2024, 11, 20, 9, 30), False, coefs))
    curves.append(exponential_decay(datetime(2024, 11, 20, 16, 00), datetime(2024, 11, 20, 19, 15), False, coefs))
    curves.append(exponential_decay(datetime(2024, 11, 21, 14, 00), datetime(2024, 11, 21, 17, 35), False, coefs))
    curves.append(exponential_decay(datetime(2024, 11, 22, 13, 55), datetime(2024, 11, 22, 18, 40), False, coefs))
    curves.append(exponential_decay(datetime(2024, 11, 23, 18, 5), datetime(2024, 11, 23, 20, 00), False, coefs))

    curves.append(exponential_decay(datetime(2024, 11, 22, 5, 40), datetime(2024, 11, 22, 9, 25), True, coefs))
    curves.append(exponential_decay(datetime(2024, 11, 23, 6, 20), datetime(2024, 11, 23, 11, 30), True, coefs))
    curves.append(exponential_decay(datetime(2024, 11, 24, 8, 25), datetime(2024, 11, 24, 12, 00), True, coefs))
    min_index = min([len(curve) for curve in curves]) - 1

    fig, axs = plt.subplots(nrows=2, sharex=True)
    for ax, label, pretty in zip(axs, ["rco2", "tvoc"], ["CO2 (ppm)", "TVOC (ppm)"]):
        for curve in curves:
            curve.rescale(min_index, label)
            ax.plot(curve.data_timedeltas, curve.rescaled_data[label], label=f"Window Open: {curve.window_open}")
        ax.set_ylabel(pretty)
        ax.legend()
   # for curve in curves:
   #     curve.rescale(min_index, "rco2")
   #     plt.plot(curve.data_timedeltas, curve.rescaled_data["rco2"], label=f"Window Open: {curve.window_open}")

    plt.legend()
    plt.show()

    simple_plot(times, data_dict)
    
    #exponentials_plots(locationId, coefs)
    
    #get_live_data(locationId, coefs)




if __name__ == "__main__":
    initialise()
