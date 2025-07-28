import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def get_db_connection():
    return sqlite3.connect('pagespeed.db', check_same_thread=False)

@st.cache_data
def load_data():
    conn = get_db_connection()
    try:
        data = pd.read_sql("SELECT * FROM pagespeed_results", conn)
        
        if 'poll_time' in data.columns:
            data['poll_time'] = pd.to_numeric(data['poll_time'])
            data['datetime'] = pd.to_datetime(data['poll_time'], unit='s')
            
        return data
    finally:
        conn.close()

def plot_url_metrics(url_data, url, strategy):
    if not url_data.empty and selected_metrics:
        fig, ax = plt.subplots(figsize=(10, 5))
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(selected_metrics)))
        
        for i, metric in enumerate(selected_metrics):
            ax.plot(
                url_data['datetime'],
                url_data[metric],
                label=metric.upper(),
                color=colors[i],
                marker='o',
                linewidth=2
            )
        
        ax.set_title(f"URL: {url} ({strategy})")
        ax.set_xlabel('Date')
        ax.set_ylabel('Score')
        ax.grid(True)
        ax.legend()
        plt.xticks(rotation=45)
        st.pyplot(fig)

def display_url_metrics(data, selected_urls):
    if not selected_urls or not selected_metrics:
        return
    
    st.header("Performance Averages")
    
    # Create columns for each URL
    url_cols = st.columns(len(selected_urls))
    
    for i, url in enumerate(selected_urls):
        url_data = data[data['url'] == url]
        if not url_data.empty:
            with url_cols[i]:
                st.subheader(f"{url[:30]}..." if len(url) > 30 else url)
                for metric in selected_metrics:
                    avg_val = url_data[metric].mean()
                    st.metric(
                        f"Avg {metric.upper()}",
                        f"{avg_val:.1f}",
                        help=f"Average for {url}"
                    )

def main():
    st.title("Pagespeed Insights Visualizer")
    
    data = load_data()
    
    if data.empty:
        st.warning("Could not find db data.")
        st.stop()
    
    # Sidebar
    st.sidebar.header("Filters")
    
    # Date
    if 'datetime' in data.columns:
        min_date = data['datetime'].min().to_pydatetime().date()
        max_date = data['datetime'].max().to_pydatetime().date()
        
        selected_dates = st.sidebar.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(selected_dates) == 2:
            start_date = pd.to_datetime(selected_dates[0])
            end_date = pd.to_datetime(selected_dates[1]) + pd.Timedelta(days=1)
            data = data[data['datetime'].between(start_date, end_date)]
    
    # URL
    if 'url' in data.columns:
        urls = data['url'].unique().tolist()
        selected_urls = st.sidebar.multiselect(
            "URLs to analyze",
            options=urls,
            default=urls[:1] 
        )
        data = data[data['url'].isin(selected_urls)]
    
    # Metric
    available_metrics = [col for col in ['performance','fcp', 'lcp', 'cls'] if col in data.columns]
    global selected_metrics
    selected_metrics = st.sidebar.multiselect(
        "Metrics to display",
        options=available_metrics,
        default=available_metrics[:1] 
    )
    
    # Strategy
    if 'strategy' in data.columns:
        selected_strategy = st.sidebar.radio(
            "Device strategy",
            options=data['strategy'].unique(),
            horizontal=True
        )
        data = data[data['strategy'] == selected_strategy]
    
    display_url_metrics(data, selected_urls)
    
    # Separate graphs for each URL
    st.header("Performance Charts")
    if selected_urls and selected_metrics:
        for url in selected_urls:
            url_data = data[data['url'] == url]
            if not url_data.empty:
                strategy = url_data['strategy'].iloc[0] if 'strategy' in url_data.columns else ''
                plot_url_metrics(url_data, url, strategy)
    
    # Raw data
    with st.expander("View Raw Data"):
        st.dataframe(data.sort_values('datetime', ascending=False))

if __name__ == "__main__":
    main()