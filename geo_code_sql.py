import requests
import json
import pandas as pd
from datetime import datetime
import string
import PySimpleGUI as sg
import sqlite3

conn = sqlite3.connect('HdDB.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS HDDistances(ReferenceNumber number UNIQUE PRIMARY KEY,
	Vin text, 
	CustomerName text, 
	Address text, 
	VehicleSubStatus text,
	OrderType text,  
	TravelTime number, 
	Distance number)''')

conn.commit()



date = datetime.now().strftime("_%Y%m%d")


#Read and Create dataframe
def create_df(file_read):
	if '.csv' in file_read:
		df = pd.read_csv(file_read, index=None)
		print('Reading .csv...')
	elif '.xlsx' in file_read:
		df = pd.read_excel(file_read, index=None)
		print('Reading .xlsx...')
	else:
		print('file type invalid!')

	df.dropna(how='all')
	#Combine address columns into single usable address
	mylambda = lambda x : x.title()
	df.DeliveryAddress = df.DeliveryAddress.apply(mylambda)
	df.DeliveryZip = df.DeliveryZip.apply(lambda x: str(x))
	df['Address'] = df['DeliveryAddress'] + ' ' + df['DeliveryZip'] + ' ' + df['DeliveryCity']

	#Create new dataframe to be used to create geocode

	df['EncodedAddress'] = df.DeliveryAddress.apply(encode_address)
	encoded_df_new = df[['ReferenceNumber','Vin', 'CustomerName', 'Address', 'OrderType', 'VehicleSubStatus', 'EncodedAddress', 'DeliveryZip', 'DeliveryCity']]
	print('Geocoding Addresses...')
	encoded_df_new['Geocode'] = encoded_df_new.apply(geo_code, axis=1)

	#Convert Geocoded Column into DistanceMatrix values
	print('Calculating Distance Matrices...')
	encoded_df_new[['TravelTime', 'Distance']] = encoded_df_new.apply(distance_matrix, axis=1, result_type='expand')

	#Strip 'RN' from ReferenceNumber to be used as Unique key in SQL server
	encoded_df_new['ReferenceNumber'] = encoded_df_new.ReferenceNumber.apply(lambda x: x.strip('RN'))
	geocoded_df = encoded_df_new[['ReferenceNumber','Vin', 'CustomerName', 'Address', 'VehicleSubStatus','OrderType', 'TravelTime', 'Distance']]
	return geocoded_df

# Convert address into HTML query format
def encode_address(address_data): 
	for x in string.punctuation:
		if x != '.':
			address_data = address_data.replace(x, '%20')
		else:
			address_data = address_data.replace(x, '')
	address_data = address_data.replace(' ', '%20')
	return address_data

#Convert address to geocode coordinates
def geo_code(data): 
	address, zipcode, city = data['EncodedAddress'], data['DeliveryZip'], data['DeliveryCity']
	headers = {
	    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
	}
	call = requests.get('https://api.openrouteservice.org/geocode/search/structured?api_key=5b3ce3597851110001cf62487e38ccf07c2b4551ba276fa19e10ecdb&address={0}%2029&postalcode={1}&locality={2}'.format(address, zipcode, city), headers=headers)

	print(call.status_code, call.reason)
	geo_json = json.loads(call.text)
	coords = [x for x in geo_json['features'][0]['geometry']['coordinates']]
	#google_style_coords = coords.reverse() #coordinates listed as latitude, longitude for use with GoogleMaps
	return coords # longitude,latitude

#Calculate distance Matrix
def distance_matrix(geo_data):
	
	geocode_column = geo_data['Geocode'] 
	#Amflughafen = [13.541659971638602, 52.37798921652795]
	location = {'Am-Flughafen': [13.541659971638602, 52.37798921652795]} #dictionary of location coordinates

	body = {"locations":[location['Am-Flughafen'], geocode_column],"metrics":["distance","duration"],"units":"km"}

	headers = {
		    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
		    'Authorization': '5b3ce3597851110001cf62487e38ccf07c2b4551ba276fa19e10ecdb',
		    'Content-Type': 'application/json; charset=utf-8'
		}
	call = requests.post('https://api.openrouteservice.org/v2/matrix/driving-car', json=body, headers=headers)

	print(call.status_code, call.reason)
	z = json.loads(call.text)
	#print(z)

	time_to_loc = int(z['durations'][0][1] / 60)
	distance_to_loc = z['distances'][0][1]

	return time_to_loc, distance_to_loc

#Export to excel
def new_excel(encoded_df):

	encoded_df.to_sql('HDDistances', conn, if_exists='append', index = False)
	encoded_df.to_excel('HomeDelivery_DistanceMatrix_'+date+'.xlsx', index=False, engine='openpyxl')

def GeoGui():
	menu_def = [['File', 'Exit'],
	['Help', 'About']]

	#Theme 
	sg.theme('dark grey 9')


	#set GUI layout
	layout = [[sg.Menu(menu_def, )],
	[sg.Text('Select File (.xlsx or .csv): '), sg.In(key='ZiplabsReport'), sg.FileBrowse(target='ZiplabsReport', size=(10, 1))],
	[sg.Button('Generate', size=(72, 1))],
	[sg.Button('Export', size=(72, 1))],
	[sg.Multiline(size=(80,20), autoscroll=True, write_only=True, auto_refresh=True, reroute_stdout=True, )]]

	window = sg.Window('Distance Matrix Finder', layout)

		#Loop
	while True:
		event, values = window.read()
		if event == 'Generate':
			file_read = values['ZiplabsReport']
			try:
				encoded_df = create_df(file_read)
				print('Preview\n', encoded_df.head())
				window.Refresh()
			except Exception as e: print(e)
		if event == 'Export':
			try:
				new_excel(encoded_df)
				print('Exporting to Database...')
				print('Exporting New Excel...')
				print('Successful!')
				window.Refresh()
			except Exception as e: print(e)			
		if event == 'About':      
			sg.popup('About this program', 'Version 1.0', 'Created by Emmanuel Kaunda') 
		if event == sg.WINDOW_CLOSED or event == 'Exit':
			c.close()
			break

############### PROGRAM MAIN ####################

GeoGui()

'''encoded_df = create_df(file_read)
print('Exporting New Excel...')
new_excel(encoded_df)'''
