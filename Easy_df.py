import pandas as pd
import string
from datetime import datetime

file_to_read = "C:/Users/ekaunda/Downloads/HDDistanceMatrix_20210414_103615.xlsx"

class Dataframe:

	def __init__(self):
		self.read_filename = ''
		self.df = pd.DataFrame()
		self.file_type = ''
		self.df_size = 0
		self.dataframes = []
		self.cols = []
		self.export_folder = 'C:/Users/ekaunda/Desktop/outputs/'

	def create_df(self, read_filename):

		self.read_filename = read_filename

		if '.csv' in self.read_filename:
			self.df = pd.read_csv(self.read_filename, index_col=None)
			self.file_type = '.csv'
			print('Reading .csv...')

		elif '.xlsx' in self.read_filename:
			self.df = pd.read_excel(self.read_filename, index_col=None)
			self.file_type = '.xlsx'
			print('Reading .xlsx...')

		else:
			print('file type invalid!')

		return self.df

	def add_df(self, dataframe_to_add):
		self.dataframes.append(dataframe_to_add)
		print('Dataframe added: ', dataframe_to_add)
		return

	def edit_df(self, df):

		choices ={}
		self.cols = [str(i) for i in self.df.columns.tolist()]

		for x in range(len(self.cols)):
			choices[x+1] = self.cols[x]
			print(x+1, self.cols[x])

		choice = input("Choose the column(s) you would like in your report (use number(s) seperated by a ','): ")
		choice_list = choice.split(',')

		new_columns = []

		for i in choice_list:
			new_columns.append(choices.get(int(i)))

		print('You have chosen the following columns: ', new_columns)
		confirm = input('If this is correct (Y/N)? ')
		if confirm.lower() == 'y':
			self.cols = new_columns
			self.df = self.df[self.cols]
			print('Successfully edited Dataframe')
			print(self.df.head())
		else:
			pass
		#print('You have chosen to group columns by {0}'.format(self.cols[s]))

	def group_df(self):

		self.cols = [str(i) for i in self.df.columns.tolist()]

		for x in range(len(self.cols)):
			print(x+1, self.cols[x])

		choice = input('Choose a column to groupby: ')
		s = int(choice) - 1
		print('You have chosen to group columns by {0}'.format(self.cols[s]))

		column_name = self.cols[s]

		names = [x for x in self.df[column_name].unique()]
		grouped = []

		for name in names:
			grouped_df = self.df[self.df[column_name] == name]
			val = {name: grouped_df}
			self.dataframes.append(val)

	#Export dataframes to csv files
	def csv_exporter(self):
		date = datetime.now().strftime("_%Y%m%d")
		if len(self.dataframes) > 1:
			file_out = [self.export_folder + k + '.csv' for data_dict in self.dataframes for k in data_dict]

			for i in range(len(self.dataframes)):
				for k,v in self.dataframes[i].items():
					v.to_csv(file_out[i])
					print('Successfully exported {0} data to {1}'.format(k, self.export_folder))

		
		elif len(self.dataframes) == 1:
			file_out = self.export_folder + 'test_file_name_{0}.csv'.format(date)
			for i in self.dataframes:
				i.to_csv(file_out)


	#Export dataframes to excel files
	def excel_exporter(self):
		date = datetime.now().strftime("_%Y%m%d")
		if len(self.dataframes) > 1:
			file_out = [self.export_folder + k + '.xlsx' for data_dict in self.dataframes for k in data_dict]

			for i in range(len(self.dataframes)):
				for k,v in self.dataframes[i].items():
					v.to_csv(file_out[i])
					print('Successfully exported {0} data to {1}'.format(k, self.export_folder))


		elif len(self.dataframes) == 1:
			file_out = self.export_folder + 'test_file_name_{0}.csv'.format(date)
			for i in self.dataframes:
				i.to_csv(file_out)



############## Testing #####################
'''obj = Dataframe()
new_obj = obj.create_df(file_to_read)
obj.edit_df(new_obj)'''
