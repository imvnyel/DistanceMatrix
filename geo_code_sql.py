import requests
import json
import pandas as pd
from datetime import datetime
import string
import PySimpleGUI as sg
import sqlite3



#create a list to temporarily save dataframes for exporting at a later time
dataframe_library = []


#Database for exporting DistMatrix
conn = sqlite3.connect('HdDB.db')
c = conn.cursor()

#Database for logging
log_conn = sqlite3.connect('FileLog.db')
l = log_conn.cursor()

#Check if file has already been converted
def already_generated(file_read):

	l.execute("select FILENAME from CREATED_FILES where FILENAME=?", (file_read,))
	data = l.fetchall()
	print(data)
	if data == file_read:
		return True
	else:
		return False

#Track which files have already been Converted
def log_db(file_read):
	l.execute('''CREATE TABLE IF NOT EXISTS CREATED_FILES(id INT AUTO_INCREMENT PRIMARY KEY, 
		FILENAME text UNIQUE,
		DATE_CREATED timestamp)''')
	print('table cerated')

	save_sql = '''INSERT INTO CREATED_FILES (FILENAME, DATE_CREATED) VALUES(?, ?)'''

	val = (file_read, datetime.now().strftime("%Y%m%d_%H%M"))
	print(val)
	l.execute(save_sql, tuple(val))

	log_conn.commit()

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

	#Beautify the addresses
	mylambda = lambda x : x.title()

	df.DeliveryAddress = df.DeliveryAddress.apply(mylambda)
	
	df.DeliveryZip = df.DeliveryZip.apply(lambda x: str(x))
	
	df['Address'] = df['DeliveryAddress'] + ' ' + df['DeliveryZip'] + ' ' + df['DeliveryCity']

	#Create new column with encoded address
	df['EncodedAddress'] = df.DeliveryAddress.apply(encode_address)
	encoded_df = df[['ReferenceNumber','Vin', 'CustomerName', 'Address', 'OrderType', 'VehicleSubStatus', 'EncodedAddress', 'DeliveryZip', 'DeliveryCity']]
	
	return encoded_df

def converter(geocode_df): #Process GEOCODING & DISTANCE MATRIX

	print('Geocoding Addresses...')
	geocode_df['Geocode'] = geocode_df.apply(geo_code, axis=1)
	#geocode_df = df[['ReferenceNumber','Vin', 'CustomerName', 'Address', 'OrderType', 'VehicleSubStatus','Geocode', 'EncodedAddress', 'DeliveryZip', 'DeliveryCity']]


	#Convert Geocoded Column into DistanceMatrix values
	print('Calculating Distance Matrices...')
	geocode_df[['TravelTime', 'Distance']] = geocode_df.apply(distance_matrix, axis=1, result_type='expand')

	#Strip 'RN' from ReferenceNumber to be used as Unique key in SQL server
	geocode_df['ReferenceNumber'] = geocode_df.ReferenceNumber.apply(lambda x: x.strip('RN'))
	convertered_df = geocode_df[['ReferenceNumber','Vin', 'CustomerName', 'Address', 'VehicleSubStatus','OrderType', 'TravelTime', 'Distance']]
	
	return convertered_df


def encode_address(address_data): #Convert address into HTML query format
	for x in string.punctuation:
		if x != '.':
			address_data = address_data.replace(x, '%20')
		else:
			address_data = address_data.replace(x, '')
			
	address_data = address_data.replace(' ', '%20')
	
	return address_data


def geo_code(data): #Convert address to geocode coordinates
	address, zipcode, city = data['EncodedAddress'], data['DeliveryZip'], data['DeliveryCity']
	
	headers = {
	    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
	}
	call = requests.get('https://api.openrouteservice.org/geocode/search/structured? \
			    api_key=5b3ce3597851110001cf62487e38ccf07c2b4551ba276fa19e10ecdb\
			    &address={0}%2029&postalcode={1}&locality={2}'.format(address, zipcode, city), headers=headers)

	print(call.status_code, call.reason)
	
	geo_json = json.loads(call.text)
	
	try:
		coords = [x for x in geo_json['features'][0]['geometry']['coordinates']]

		return coords # longitude,latitude
	
		try:
			print('There was a problem GEOCODING address, please ensure address is correctly written: ', data['DeliveryCity'])
			coords = []
			
			return coords
		
		except Exception as e: print(e)
			
	except Exception as e: print(e)


def distance_matrix(geo_data): #Calculate Distance Matrix
	
	geocode_column = geo_data['Geocode']
	
	#dictionary of location coordinates
	location = {'Am-Flughafen': [13.541659971638602, 52.37798921652795]}

	body = {"locations":[location['Am-Flughafen'], geocode_column],"metrics":["distance","duration"],"units":"km"}

	headers = {
		    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
		    'Authorization': '5b3ce3597851110001cf62487e38ccf07c2b4551ba276fa19e10ecdb',
		    'Content-Type': 'application/json; charset=utf-8'
		}

	try:
		call = requests.post('https://api.openrouteservice.org/v2/matrix/driving-car', json=body, headers=headers)

		print(call.status_code, call.reason)
		z = json.loads(call.text)
		#print(z)

		time_to_loc = int(z['durations'][0][1] / 60)
		distance_to_loc = z['distances'][0][1]

		return time_to_loc, distance_to_loc
	except:
		if geocode_column == []:
			time_to_loc = 0
			distance_to_loc = 0
			return time_to_loc, distance_to_loc


def new_db(DistMat_df): #Export to database


	#Create new Table or ignore if exists
	c.execute('''CREATE TABLE IF NOT EXISTS HDDistances(ReferenceNumber number UNIQUE PRIMARY KEY,
	Vin text, 
	CustomerName text, 
	Address text, 
	VehicleSubStatus text,
	OrderType text,  
	TravelTime number, 
	Distance number)''')

	#create columns list for items to be inserted into columns
	cols = "','".join([str(i)for i in DistMat_df.columns.tolist()])

	#create insert into statement to insert individual rows into database
	for i, row in DistMat_df.iterrows():
		sql = "REPLACE INTO 'HDDistances' ('" +cols + "') VALUES (" + "?,"*(len(row)-1) + "?)"
		c.execute(sql, tuple(row))

	conn.commit()

#Export to excel
def new_excel(DistMat_df):

	#Generate date for filenaming
	date = datetime.now().strftime("_%Y%m%d")
	DistMat_df.to_excel('HomeDelivery_DistanceMatrix_'+date+'.xlsx', index=False, engine='openpyxl')


def GeoGui():
	menu_def = [['File', 'Exit'],
	['Help', 'About']]

	#Theme 
	sg.theme('dark grey 9')

	#set GUI layout
	layout = [[sg.Menu(menu_def, )],
	[sg.Text('Select File (.xlsx or .csv): '), sg.In(key='ZiplabsReport'), sg.FileBrowse(target='ZiplabsReport', size=(10, 1))],
	[sg.Button('Intialize', size=(72, 1))],
	[sg.Button('Generate Distance Matrix', size=(72, 1))],
	[sg.Button('Export to Excel', size=(35, 1)), sg.Button('Export to Database', size=(35, 1))],
	[sg.Multiline(size=(80,20), autoscroll=True, write_only=True, auto_refresh=True, reroute_stdout=True, )]]

	window = sg.Window('Distance Matrix Finder', layout)

	#Loop
	while True:
		event, values = window.read()

		if event == 'Intialize':
			file_read = values['ZiplabsReport']
			try:
				check = already_generated(file_read)
				
				if check is True:
					encoded_df = create_df(file_read)
					dataframe_library.append(encoded_df)
					print('Preview\n', encoded_df.head())
					window.Refresh()
				else:
					print ('File has already been created')
					
			except Exception as e: print(e)

		if event == 'Generate Distance Matrix':
			try:
				DistMat_df = converter(encoded_df)
				
			except Exception as e: print(e)

		if event == 'Export to Excel':
			file_read = values['ZiplabsReport']
			try:
				new_excel(DistMat_df)
				print('Exporting New Excel...')
				print('Successful!')
				log_db(file_read)
				window.Refresh()
			except Exception as e: print(e)

		if event == 'Export to Database':
			file_read = values['ZiplabsReport']
			try:
				new_db(DistMat_df)
				print('Exporting to Database...')
				print('Successful!')
				log_db(file_read)
				window.Refresh()
			except Exception as e: print(e)

		if event == 'About':      
			sg.popup('About this program', 'Version 1.0', 'Created by Emmanuel Kaunda')

		if event == sg.WINDOW_CLOSED or event == 'Exit':
			c.close()
			l.close()
			break

############### PROGRAM MAIN ####################
GeoGui()
