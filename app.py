from flask import Flask, render_template
from flask import *
import cProfile
import pstats
import io
import matplotlib.pyplot as plt
import re
import pandas as pd
import base64
import seaborn as sns
import matplotlib
matplotlib.use('agg')

app = Flask(__name__)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    name1 = file.filename
    if file.filename == '':
        return 'No selected file'

    # Process the uploaded file (e.g., analyze its content)
    content = file.read()  # Read the content of the uploaded file use
    # Add your analysis logic here
    profile_data = profile_code(content)
    print(profile_data)
    #df = parse_profile_data(profile_data)
    df_cumtime, df_tottime, df_ncalls = parse_profile_data(profile_data)
    # Create visualizations
    plot_paths = create_visualizations(df_cumtime, df_tottime, df_ncalls)
    summary = extract_summary(df_cumtime, df_tottime, df_ncalls)
    return render_template('index.html', profile_data=profile_data, content=content, plot_paths=plot_paths, summary=summary)


def profile_code(code):
    pr = cProfile.Profile()
    pr.enable()
    exec(code)
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    return s.getvalue()


def parse_profile_data(profile_data):
    profile_list = profile_data.strip().split('\n')
    data_cumtime = [line.split(None, 5) for line in profile_list[1:] if line.strip()]
    columns = ['ncalls', 'tottime', 'percall', 'cumtime', 'percall', 'filename:lineno(function)']
    df_cumtime = pd.DataFrame(data_cumtime, columns=columns)

    # Parsing for total time
    data_tottime = [line.split(None, 5) for line in profile_list[1:] if line.strip()]
    df_tottime = pd.DataFrame(data_tottime, columns=columns)

    # Parsing for function call counts
    data_ncalls = [line.split(None, 5) for line in profile_list[1:] if line.strip()]
    df_ncalls = pd.DataFrame(data_ncalls, columns=columns)

    return df_cumtime, df_tottime, df_ncalls
    # Parse the profiling data into a DataFrame
    # profile_list = profile_data.strip().split('\n')
    # data = [line.split(None, 5) for line in profile_list[1:]]
    # columns = ['ncalls', 'tottime', 'percall', 'cumtime', 'percall', 'filename:lineno(function)']
    # df = pd.DataFrame(data, columns=columns)
    # return df


def create_visualizations(df_cumtime, df_tottime, df_ncalls):
    # bar plot of 'cumtime' for each function
    plot_paths = []
    plt.figure(figsize=(18, 12))
    sns.barplot(x='cumtime', y='filename:lineno(function)', data=df_cumtime)
    plt.xlabel('Cumulative Time (s)')
    plt.ylabel('Function')
    plt.title('Cumulative Time by Function')
    plot_path = '/static/plot.png'
    # Save the plot as a static file
    plot_paths.append(plot_path)
    plt.savefig('static/plot.png')

    # Total Time
    plt.figure(figsize=(18, 12))
    sns.barplot(x='tottime', y='filename:lineno(function)', data=df_tottime)
    plt.xlabel('Total Time (s)')
    plt.ylabel('Function')
    plt.title('Total Time by Function')
    plot_path_tottime = '/static/plot_tottime.png'
    plt.savefig('static/plot_tottime.png')
    plot_paths.append(plot_path_tottime)

    # Function Call Counts
    plt.figure(figsize=(18, 12))
    sns.barplot(x='ncalls', y='filename:lineno(function)', data=df_ncalls)
    plt.xlabel('Function Call Counts')
    plt.ylabel('Function')
    plt.title('Function Call Counts by Function')
    plot_path_ncalls = '/static/plot_ncalls.png'
    plt.savefig('static/plot_ncalls.png')
    plot_paths.append(plot_path_ncalls)

    return plot_paths


def extract_summary(df_cumtime, df_tottime, df_ncalls):
    try:
        # Convert relevant columns to numeric types
        numeric_columns = ['cumtime', 'tottime', 'ncalls']

        for column in numeric_columns:
            df_cumtime[column] = pd.to_numeric(df_cumtime[column], errors='coerce')
            df_tottime[column] = pd.to_numeric(df_tottime[column], errors='coerce')
            df_ncalls[column] = pd.to_numeric(df_ncalls[column], errors='coerce')

        # Drop rows with NaN values after conversion
        df_cumtime.dropna(inplace=True)
        df_tottime.dropna(inplace=True)
        df_ncalls.dropna(inplace=True)

        # Calculate total cumulative and total time
        total_cumtime = df_cumtime['cumtime'].sum()
        total_tottime = df_tottime['tottime'].sum()

        # Calculate percentage contribution of each function to total cumulative and total time
        df_cumtime['cumtime_pct'] = (df_cumtime['cumtime'] / total_cumtime) * 100
        df_tottime['tottime_pct'] = (df_tottime['tottime'] / total_tottime) * 100

        # Identify functions with high cumulative and total times
        high_cumtime_functions = df_cumtime[df_cumtime['cumtime'] > (total_cumtime / 20)]  # Functions taking >5% of total time
        high_tottime_functions = df_tottime[df_tottime['tottime'] > (total_tottime / 20)]  # Functions taking >5% of total time

        # Calculate the total number of function calls
        total_calls = df_ncalls['ncalls'].astype(int).sum()

        # Calculate the percentage of calls for each function
        df_ncalls['ncalls_pct'] = (df_ncalls['ncalls'].astype(int) / total_calls) * 100

        # Identify functions with high call counts
        high_call_count_functions = df_ncalls[df_ncalls['ncalls'] > (total_calls / 20)]  # Functions with >5% of total calls

        summary = {
            'total_cumtime': total_cumtime,
            'total_tottime': total_tottime,
            'high_cumtime_functions': high_cumtime_functions,
            'high_tottime_functions': high_tottime_functions,
            'high_call_count_functions': high_call_count_functions
        }
        return summary
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == '__main__':
    app.run(debug=True)
