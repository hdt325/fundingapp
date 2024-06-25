import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid.shared import GridUpdateMode
from datetime import datetime, timedelta

# Import functions from the separate files
from hyperliquid import load_hyperliquid_data
from apex import get_apex_funding_rates

st.set_page_config(page_title="Funding App", page_icon=":rocket:", layout="wide", initial_sidebar_state="expanded")

def main():
    st.title("Funding Rate Comparisons")
    st.write("Recall: funding rate = what the longs pay the shorts :sunglasses:")
    st.divider()

    # Initialize session state
    if 'hyperliquid_data' not in st.session_state:
        st.session_state.hyperliquid_data = None
        st.session_state.apex_data = None
        st.session_state.last_refresh = datetime.now()
        st.session_state.num_pairs = 5  # Default to 5 pairs

    # Create two columns for input and refresh button
    col1, col2, col3 = st.columns([1, 2, 1], vertical_alignment='bottom')
    with col1:
        # Create a refresh button
        if st.button('Refresh Data'):
            st.session_state.hyperliquid_data = None
            st.session_state.apex_data = None
            st.session_state.last_refresh = datetime.now()
    with col3:
        # Add number input for selecting number of pairs
        num_pairs = st.number_input("Hyperliquid pairs to display (0 = all)", help="Hyperliquid has a lot of pairs. Showing all of them takes a long time to load.",
                                    min_value=0, label_visibility='visible',
                                    value=st.session_state.num_pairs)
        st.session_state.num_pairs = num_pairs

    # Auto-refresh every 15 minutes
    if datetime.now() - st.session_state.last_refresh > timedelta(minutes=15):
        st.session_state.hyperliquid_data = None
        st.session_state.apex_data = None
        st.session_state.last_refresh = datetime.now()
        st.experimental_rerun()

    # Load or reload data
    if st.session_state.hyperliquid_data is None or st.session_state.apex_data is None:
        with st.spinner('Loading data...'):
            st.session_state.hyperliquid_data = load_hyperliquid_data(0 if num_pairs == 0 else num_pairs)
            st.session_state.apex_data = get_apex_funding_rates()

    # Display the data
    st.write(f"Data will update every 15 mins. Last updated: {st.session_state.last_refresh.strftime('%H:%M:%S | %m/%d/%y')} PST")
    
    st.markdown(
        f"""
        <p style="font-size: 0.8em;">
        For Hyperliquid, base funding rate is 0.00125%, and premiums are added/substracted based on oracle price. 
        Funding is charged/given based on rate at the end of the hour, and rates outside of that timestamp are simply predicted values (not the actual $). 
        <a href="https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding" target="_blank">See Hyperliquid Docs</a>
        </p>
        """,
        unsafe_allow_html=True
    )

    # Hyperliquid Table
    st.subheader("Hyperliquid Funding Rates")
    display_aggrid(st.session_state.hyperliquid_data)

    # Apex Table
    st.subheader("Apex Funding Rates")
    display_aggrid(st.session_state.apex_data)

def display_aggrid(data):
    # JavaScript function for cell styling
    cell_style_jscode = JsCode("""
    function(params) {
        if (params.value) {
            var rate = parseFloat(params.value.replace('%', ''));
            if (rate > 0.00125) {
                return {'color': 'green'};
            } else if (rate < 0) {
                return {'color': '#FF6666'};
            } else {
                return {'color': 'grey'};
            }
        }
        return null;
    }
    """)

    # Configure AgGrid
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_default_column(enablePivot=True, enableValue=True, enableRowGroup=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_column("Funding Rate", cellStyle=cell_style_jscode)
    gb.configure_grid_options(domLayout='normal')
    gridOptions = gb.build()

    # Display the AgGrid
    AgGrid(
        data,
        gridOptions=gridOptions,
        height=500,
        width='100%',
        data_return_mode='AS_INPUT', 
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
    )

if __name__ == "__main__":
    main()