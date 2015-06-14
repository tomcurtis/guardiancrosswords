#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import mysql.connector
import pygal
import sys
import argparse

#set up for command line arguments
parser = argparse.ArgumentParser(description="Produce a chart comparing how frequently different words appear in Guardian crosswords.")
parser.add_argument('-q', dest="query_type", choices=['weekday', 'year', 'setter', 'type'], default='year', help="Output is grouped by weekday or year of publication, by setter or by crossword type. Default: year.")
parser.add_argument('-t', dest="chart_type", choices=['bar', 'line', 'horizontal_bar', 'stacked_bar', 'stacked_line', 'area', 'stacked_area', 'scatter'], default='bar', help="Which type of chart to produce. Default: bar")
parser.add_argument('output', help="Filename to save results to.")
parser.add_argument('word', nargs='+', help="Words to check up on.")
args = parser.parse_args()

#extract the information we need
words = [x.upper() for x in args.word]
query_type = args.query_type
chart_type = args.chart_type
if (args.output[-4:].lower() == ".svg"):
	output_file = args.output
elif (args.output == "-"): #use to redirect to stdout
	output_file = args.output
else:
	output_file = args.output + ".svg"

#connect to database
connection = mysql.connector.connect(user="root", password="password", host="127.0.0.1", database="guardian_crosswords")
cursor = connection.cursor()

#queries - with placeholders for list of words, as you can't give it a list directly
queries = {
	'year':	("SELECT words.solution, YEAR(crosswords.published) as year, count(*) "
			 "FROM words INNER JOIN crosswords ON words.crossword=crosswords.uid "
			 "WHERE words.solution in $$$$$ GROUP BY words.solution, year"),

	'weekday': ("SELECT words.solution, DAYNAME(crosswords.published) as day, count(*) "
			 	"FROM words INNER JOIN crosswords ON words.crossword=crosswords.uid "
			 	"WHERE words.solution in $$$$$ GROUP BY words.solution, day"),

	#don't let you actually use this though. looks too ugly at the moment to be useful
	'month': ("SELECT words.solution, DATE_FORMAT(crosswords.published, '%Y-%m') as month, count(*) "
		 	"FROM words INNER JOIN crosswords ON words.crossword=crosswords.uid "
		 	"WHERE words.solution in $$$$$ GROUP BY words.solution, month"),

	'setter': ("SELECT words.solution, crosswords.setter, count(*) "
			  "FROM words INNER JOIN crosswords ON words.crossword=crosswords.uid "
			  "WHERE words.solution in $$$$$ GROUP BY words.solution, crosswords.setter"),

	'type':  ("SELECT words.solution, crosswords.type, count(*) "
			  "FROM words INNER JOIN crosswords ON words.crossword=crosswords.uid "
			  "WHERE words.solution in $$$$$ GROUP BY words.solution, crosswords.type")
}

#load the list of words and extract counts from database
words_list = str(words).replace("[", "(").replace("]", ")")
query_string = queries[query_type].replace("$$$$$", words_list)
cursor.execute(query_string)

#pull out the info into a dict like {word: {key: value}}
counts_data = {}
for (word, key, count) in cursor:
	key = str(key)
	if ((query_type == "setter") and (key == "None")):
		key = "Unknown"
	if (word in counts_data):
		counts_data[word][key] = count
	else:
		counts_data[word] = {key: count}

#check we have all the words we asked for, even if nothing found
for word in words:
	if (word not in counts_data):
		counts_data[word] = {}

#need a consistent list of keys so we can make sure we have values for all points
if (query_type == 'year'):
	#if it's years, then we need the whole range
	keys_list = [str(x) for x in range(1999, 2015)]
elif (query_type == "month"):
	#if it's months, want everything from to 1999-08 to 2015-02
	keys_list = []
	for x in range(8, 13):
		keys_list.append("1999-" + str(x).zfill(2))
	for y in range(2000, 2015):
		for x in range(1, 13):
			keys_list.append(str(y) + "-" + str(x).zfill(2))
	for x in range(1, 3):
		keys_list.append("2015-" + str(x).zfill(2))
	keys_list.sort()

elif (query_type == "weekday"):
	#days are another known list - and non-alphabetical order
	keys_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
else:
	#otherwise, extract what we have
	keys_list = []
	for word in counts_data:
		for key in counts_data[word].keys():
			if (key not in keys_list):
				keys_list.append(key)
	keys_list.sort()

#now can make graph data - dict of {word: [values, values, values]}
graph_data = {}
for word in counts_data:
	graph_data[word] = {}
	for key in keys_list:
		if (key in counts_data[word]):
			count = counts_data[word][key]
		else:
			count = 0
		item = {'value': count,
				'label': word + " / " + key
				}
		graph_data[word][key] = item

#now make the chart -- need to set this value up front
x_label_rotation = 0
if (query_type == 'setter'):
	x_label_rotation = 90

#chart type depends on what we've said
if (chart_type == "bar"):
	chart = pygal.Bar(legend_at_bottom=True, pretty_print=True, print_values=False, no_prefix=True, show_dots=False, x_label_rotation=x_label_rotation, js=[])
elif (chart_type == "line"):
	chart = pygal.Line(legend_at_bottom=True, pretty_print=True, print_values=False, no_prefix=True, show_dots=False, x_label_rotation=x_label_rotation, js=[])
elif (chart_type == "scatter"):
	chart = pygal.Line(legend_at_bottom=True, pretty_print=True, print_values=False, no_prefix=True, show_dots=True, x_label_rotation=x_label_rotation, js=[], stroke=False)
elif (chart_type == "area"):
	chart = pygal.Line(legend_at_bottom=True, pretty_print=True, print_values=False, no_prefix=True, show_dots=False, x_label_rotation=x_label_rotation, fill=True, js=[])
elif (chart_type == "horizontal_bar"):
	chart = pygal.HorizontalBar(legend_at_bottom=True, pretty_print=True, print_values=False, no_prefix=True, show_dots=False, x_label_rotation=x_label_rotation, js=[])
elif (chart_type == "stacked_bar"):
	chart = pygal.StackedBar(legend_at_bottom=True, pretty_print=True, print_values=False, no_prefix=True, show_dots=False, x_label_rotation=x_label_rotation, js=[])
elif (chart_type == "stacked_line"):
	chart = pygal.StackedLine(legend_at_bottom=True, pretty_print=True, print_values=False, no_prefix=True, show_dots=False, x_label_rotation=x_label_rotation, js=[])
elif (chart_type == "stacked_area"):
	chart = pygal.StackedLine(legend_at_bottom=True, pretty_print=True, print_values=False, no_prefix=True, show_dots=False, x_label_rotation=x_label_rotation, fill=True, js=[])

chart.title = "Frequency of words in Guardian crosswords by " + query_type
chart.value_formatter = lambda x: "%.0f" % x
chart.x_title = query_type.capitalize()
chart.x_labels = keys_list
chart.y_title = "Count"
for word in sorted(graph_data):
	chart.add(word, graph_data[word])

#direct output to std out or to file specified
if (output_file == "-"):
	print(chart.render())
else:
	chart.render_to_file(output_file)