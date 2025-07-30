import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

# CONFIG
DEFAULT_DB_PATH = "pagespeed.db"
DB_PATH = os.getenv("PAGESPEED_DB_PATH", DEFAULT_DB_PATH) #EASY CUSTOMIZATION
CACHE_TTL = 3600  # 1 hour (always in seconds)

def get_db_connection():
    """CONNECT TO DB"""
    try:
        return sqlite3.connect(DB_PATH, check_same_thread=False)
    except sqlite3.Error as e:
        st.error(f"Database connection failed: {str(e)}")
        st.error(f"Tried path: {DB_PATH}")
        st.stop()

@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading...")
def load_data():
    """LOAD DATA FROM DB CONNECTION"""
    conn = get_db_connection()
    try:
        data = pd.read_sql("SELECT * FROM pagespeed_results", conn)
        
        if 'poll_time' in data.columns:
            data['poll_time'] = pd.to_numeric(data['poll_time'])
            data['datetime'] = pd.to_datetime(data['poll_time'], unit='s')
            
        return data
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def plot_url_metrics(url_data, url, strategy):
    """PLOT METRICS FOR A SPECIFIC URL"""
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
    """URL GRID FOR COLUMN METRIC AVERAGES"""
    if not selected_urls or not selected_metrics:
        return
    
    st.header("Performance Averages by URL")
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
    
    # BUTTON TO RELOAD DATA
    if st.button("Reload Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Show current configuration DEBUG INFO
    # st.sidebar.header("Configuration Info")
    # st.sidebar.write(f"Database path: `{DB_PATH}`")
    # st.sidebar.write(f"Cache TTL: {CACHE_TTL} seconds ({(CACHE_TTL/60):.1f} minutes)")
    # if DB_PATH == DEFAULT_DB_PATH:
    #     st.sidebar.info("Using default database path. Set PAGESPEED_DB_PATH environment variable to customize.")
    
    data = load_data()
    
    if data.empty:
        st.warning("No data loaded. Please check your database configuration.")
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
            default=urls[:2]
        )
        data = data[data['url'].isin(selected_urls)]
    
    # Metrics 
    available_metrics = [col for col in ['performance','fcp', 'lcp', 'cls'] if col in data.columns]
    global selected_metrics
    selected_metrics = st.sidebar.multiselect(
        "Metrics to display",
        options=available_metrics,
        default=available_metrics[:2]
    )
    
    # Strategy 
    if 'strategy' in data.columns:
        selected_strategy = st.sidebar.radio(
            "Device strategy",
            options=data['strategy'].unique(),
            horizontal=True
        )
        data = data[data['strategy'] == selected_strategy]
    
    # Display metrics
    display_url_metrics(data, selected_urls)
    
    # SEPARATE GRAPH FOR EACH URL
    st.header("Performance Trends by URL")
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