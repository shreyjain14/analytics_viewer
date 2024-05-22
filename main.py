from flask import Flask, render_template, jsonify
import psycopg2
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz

load_dotenv()

app = Flask(__name__)

# Connect to the PostgreSQL database
conn = psycopg2.connect(os.getenv('POSTGRESQL_URI'))
cur = conn.cursor()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def get_data():
    # Fetch data from the database
    cur.execute("""
        SELECT
            page,
            COUNT(*) AS views,
            DATE_TRUNC('hour', visit_time) AT TIME ZONE 'UTC' AS hour
        FROM
            analytics
        WHERE
            visit_time >= NOW() - INTERVAL '24 hours'
        GROUP BY
            page, DATE_TRUNC('hour', visit_time)
        ORDER BY
            hour DESC;
    """)
    data = cur.fetchall()

    # Create a complete list of hours for the last 24 hours
    hours = [datetime.now(pytz.utc) - timedelta(hours=i) for i in range(24)]
    hours = [hour.replace(minute=0, second=0, microsecond=0) for hour in hours]

    # Timezone conversion to IST
    ist = pytz.timezone('Asia/Kolkata')
    hours_ist = [hour.astimezone(ist) for hour in hours]

    # Prepare data for the chart
    chart_data = {}
    for page, views, hour in data:
        hour_ist = hour.astimezone(ist)
        if page not in chart_data:
            chart_data[page] = {h: 0 for h in hours_ist}
        chart_data[page][hour_ist] = views

    # Convert to the desired format
    formatted_data = {
        page: [{'x': hour.strftime('%Y-%m-%d %H:%M:%S'), 'y': views} for hour, views in sorted(hours_dict.items())]
        for page, hours_dict in chart_data.items()
    }

    # Fetch total views for specific pages in the last 24 hours
    pages = ['home', 'slayer', 'misc', 'update']
    total_views = {}
    for page in pages:
        cur.execute("""
                SELECT COUNT(*)
                FROM analytics
                WHERE page = %s AND visit_time >= NOW() - INTERVAL '24 hours'
            """, (page,))
        total_views[page] = cur.fetchone()[0]

    previous_data = fetch_previous_data()

    return jsonify(chart_data=formatted_data, total_views=total_views, previous_data=previous_data)


def fetch_previous_data():
    # Fetch data for the previous 24 hours
    cur.execute("""
        SELECT
            page,
            COUNT(*) AS views
        FROM
            analytics
        WHERE
            visit_time >= NOW() - INTERVAL '48 hours'
            AND visit_time < NOW() - INTERVAL '24 hours'
        GROUP BY
            page;
    """)
    previous_data = cur.fetchall()
    previous_data = {page: views for page, views in previous_data}
    return previous_data


if __name__ == '__main__':
    app.run(debug=True)
