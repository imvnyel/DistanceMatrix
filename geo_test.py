import converter as cnv
import Easy_df as edf
from datetime import datetime
import string
import PySimpleGUI as sg
import sqlite3

#file_to_read = "C:/Users/ekaunda/Downloads/HDDistanceMatrix_20210414_103615.xlsx"

def GeoGui():
	columns = []
	menu_def = [['File', 'Exit'],
	['Help', 'About']]

	#Theme 
	sg.theme('dark grey 9')


	#set GUI layout
	layout = [[sg.Menu(menu_def, )],
	[sg.Text('Select File (.xlsx or .csv): '), sg.In(key='ZiplabsReport'), sg.FileBrowse(target='ZiplabsReport', size=(10, 1))],
	[sg.Button('Intialize', size=(72, 1))],
	[sg.Combo(columns, key='AddressColumn', size=(30, 6))],
	[sg.Button('Generate Distance Matrix', size=(72, 1))],
	[sg.Button('Export to Excel', size=(35, 1)), sg.Button('Export to CSV', size=(35, 1))],
	[sg.Multiline(size=(80,20), autoscroll=True, write_only=True, auto_refresh=True, reroute_stdout=True, key='print_output')]]

	window = sg.Window('Distance Matrix Finder', layout, auto_size_buttons=True, auto_size_text=True ,resizable=True)

		#Loop
	while True:
		event, values = window.read()
		#db_init()

		#Initialize project. Open file, convert into a Pandas dataframe, return cleaned dataframe. 
		if event == 'Intialize':
			file_to_read = values['ZiplabsReport']
			window['print_output']('')
			try:
				#check = already_generated(file_read)
				check = False
				if check is False:
					d = edf.Dataframe()
					new_df = d.create_df(file_to_read)
					columns = [str(i) for i in new_df.columns.tolist()]
					print('Preview\n', new_df.head())
					window.Refresh()
					window.FindElement('AddressColumn').Update(values=columns)
				else:
					print ('File has already been created')
			except Exception as e: print(e)

		#First convert address to Geocode, then use geocode to get Distance matrix
		if event == 'Generate Distance Matrix':
			try:
				#Take dataframe and process to return Geocode and Distance Matrix
				c = cnv.Converter(new_df)
				addressed_df = c.address_convert()

				#Geocode
				geocoded = c.geocode(addressed_df)

				#Distance Matrix
				Dmat_df = c.distancematrix(geocoded)

				#Add processed dataframe to list for exporting
				d.add_df(Dmat_df)

				print('DistanceMatrix complete, please choose an export method')
			except Exception as e: print(e)

		#Export dataframe with completed DM columns to Excel
		if event == 'Export to Excel':
			file_to_read = values['ZiplabsReport']
			try:

				#export dataframe(s)
				print('Staring Excel Exporter...')
				d.excel_exporter()

				print('Exporting New Excel...')
				print('Successful!')

				#log_db(file_to_read)
				window.Refresh()
			except Exception as e: print(e)

		#Export dataframe with completed DM columns to Excel
		if event == 'Export to CSV':
			file_to_read = values['ZiplabsReport']
			try:

				#export dataframe(s)
				print('Staring CSV Exporter...')
				d.csv_exporter()

				print('Exporting to Database...')
				print('Successful!')
				#log_db(file_to_read)
				window.Refresh()


			except Exception as e: print(e)

		if event == 'About':      
			sg.popup('About this program', 'Version 1.0', 'Created by Emmanuel Kaunda')

		if event == sg.WINDOW_CLOSED or event == 'Exit':
			#c.close()
			#l.close()
			break

############### PROGRAM MAIN ####################
GeoGui()

