import requests
import json
import pandas as pd
from datetime import datetime
import string
import sqlite3
pd.options.mode.chained_assignment = None  # default='warn'


class Converter:

	def __init__(self, data):
		self.data = data
		self.file_type = ''
		self.stored_df = []

	def address_convert(self):
		self.data.dropna(how='all')

		#Combine address columns into single usable address
		mylambda = lambda x : x.title()
		self.data.DeliveryAddress = self.data.DeliveryAddress.apply(mylambda)
		self.data.DeliveryZip = self.data.DeliveryZip.apply(lambda x: str(x))
		self.data['Address'] = self.data['DeliveryAddress'] + ' ' + self.data['DeliveryZip'] + ' ' + self.data['DeliveryCity']

		#Create new dataframe to be used to create geocode
		self.data['EncodedAddress'] = self.data.DeliveryAddress.apply(self.encode_address)
		self.encoded_df = self.data[['ReferenceNumber','Vin', 'CustomerName', 'Address', 'OrderType', 'VehicleSubStatus', 'EncodedAddress', 'DeliveryZip', 'DeliveryCity']]
		return self.encoded_df		

	def geocode(self, reg_df):
		print('Geocoding Addresses...')
		reg_df['Geocode'] = reg_df.apply(self.geo_code_API, axis=1)
		self.geocode_df = reg_df[['ReferenceNumber','Vin', 'CustomerName', 'Address', 'OrderType', 'VehicleSubStatus','Geocode', 'EncodedAddress', 'DeliveryZip', 'DeliveryCity']]
		return self.geocode_df
	
	def distancematrix(self, geocode_df):
		print('Calculating Distance Matrices...')
		geocode_df[['TravelTime', 'Distance']] = geocode_df.apply(self.distance_matrix_API, axis=1, result_type='expand')
		self.dm_df = geocode_df[['ReferenceNumber','Vin', 'CustomerName', 'Address', 'VehicleSubStatus','OrderType', 'TravelTime', 'Distance']]
		return self.dm_df



	#### These functions are used by the methods in this class. They should not be called ####
		
	#Make address into a html query-able format
	def encode_address(self, address_encoded): 
		for x in string.punctuation:
			if x != '.':
				address_encoded = address_encoded.replace(x, '%20')
			else:
				address_encoded = address_encoded.replace(x, '')
		address_encoded = address_encoded.replace(' ', '%20')
		return address_encoded

	#Connect to geocode API Convert address to geocode coordinates
	def geo_code_API(self, address_data): 
		address, zipcode, city = address_data['EncodedAddress'], address_data['DeliveryZip'], address_data['DeliveryCity']
		headers = {
		    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
		}
		call = requests.get('https://api.openrouteservice.org/geocode/search/structured?api_key=5b3ce3597851110001cf62487e38ccf07c2b4551ba276fa19e10ecdb&address={0}%2029&postalcode={1}&locality={2}'.format(address, zipcode, city), headers=headers)

		print(call.status_code, call.reason)
		geo_json = json.loads(call.text)
		try:
			coords = [x for x in geo_json['features'][0]['geometry']['coordinates']]
			print(coords)
			return coords # longitude,latitude
			try:
				print('There was a problem GEOCODING address, please ensure address is correctly written: ', address_data['DeliveryCity'])
				coords = []
				return coords
			except Exception as e: print(e)
		except Exception as e: print(e)

	#Connect to Distance Matrix API to Calculate distance Matrix
	def distance_matrix_API(self, geo_data):
		
		geocode_column = geo_data['Geocode'] 
		#Amflughafen = [13.541659971638602, 52.37798921652795]
		location = {'Am-Flughafen': [13.541659971638602, 52.37798921652795]} #dictionary of location coordinates


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