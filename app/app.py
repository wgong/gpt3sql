"""
Streamlit app to experiment with GPT3 models
"""
#####################################################
# Imports
#####################################################
# generic import
from datetime import date, datetime, timedelta
from uuid import uuid4
import sqlite3
import pandas as pd

import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

# import modules of this app 
from api.gpt import *
from cfg.settings import *

_STR_APP_NAME               = "GPT-3 SQL"
_STR_MENU_HOME              = "Welcome"
_STR_MENU_SQL_GEN           = "Generate SQL"
_STR_MENU_SQL_RUN           = "Execute SQL"
_STR_MENU_SQLITE_SAMPLE     = "Explore SQLite Sample DB"
_STR_MENU_SETTINGS          = "Configure Settings"

st.set_page_config(
     page_title=f'{_STR_APP_NAME}',
     layout="wide",
     initial_sidebar_state="expanded",
)

#####################################################
# Helpers
#####################################################

class DBConn(object):
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file)
    def __enter__(self):
        return self.conn
    def __exit__(self, type, value, traceback):
        self.conn.close()

def get_tables():
    with DBConn() as _conn:
        sql_stmt = f'''
        SELECT 
            name
        FROM 
            sqlite_schema
        WHERE 
            type ='table' AND 
            name NOT LIKE 'sqlite_%';
        '''
        df = pd.read_sql(sql_stmt, _conn)
        return df["name"].to_list()

#####################################################
# Menu Handlers
#####################################################
def go_home():
    st.subheader(f"{_STR_MENU_HOME}")
    st.markdown("""
    This [streamlit](https://streamlit.io/) app helps one explore [GPT-3 Codex capability](https://beta.openai.com/docs/guides/code/introduction) in terms of SQL generation
    - Experiment with GPT-3 capability [at Playground](https://beta.openai.com/playground?mode=complete)
    - Validate generated SQL against a [SQLite sample dataset](https://www.sqlitetutorial.net/sqlite-sample-database/)

    """, unsafe_allow_html=True)

def do_sql_gen():
    st.subheader(f"{_STR_MENU_SQL_GEN}")
    prompt_value = '''
    Table customers, columns = [CustomerId, FirstName, LastName,  State]
    Create a SQLite query for all customers in Texas named Jane
    '''
    prompt = st.text_area("Prompt:", value=prompt_value, height=200)
    prompts = [i.strip() for i in prompt.split('\n') if i.strip()]
    # st.write(prompt)
    if st.button("Submit"):
        openai.api_key = OPENAI_API_KEY
        openai_mode = st.session_state.get("openai_mode", "Complete")
        if openai_mode != "Complete":
            st.error(f"OpenAI mode {openai_mode} not yet implemented")
            return

        response = openai.Completion.create(
            model=st.session_state.get("openai_model", "davinci-instruct-beta"), 
            prompt="\"\"\"\n" + '\n'.join(prompts) + "\n\"\"\"\n\n\n",
            temperature=st.session_state.get("openai_temp", 0),
            max_tokens=st.session_state.get("openai_max_token", 256),
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        resp_str = response["choices"][0]["text"]
        st.write("Response:")
        st.info(resp_str.split('"""')[0])

def do_sql_run():
    st.subheader(f"{_STR_MENU_SQL_RUN}")
    st.session_state["GENERATED_SQL_STMT"] = "select * from customers limit 10;"
    gen_sql_stmt = st.session_state["GENERATED_SQL_STMT"]
    sql_stmt = st.text_area("Generated SQL:", value=gen_sql_stmt, height=200)
    if st.button("Execute Query ..."):
        with DBConn() as _conn:
            df = pd.read_sql(sql_stmt, _conn)
            st.dataframe(df)


def do_sqlite_sample_db():
    st.subheader(f"{_STR_MENU_SQLITE_SAMPLE}")
    tables = get_tables()
    idx_default = tables.index("customers") if "customers" in tables else 0
    table_name = st.selectbox("Table:", tables, index=idx_default, key="table_name")
    sql_stmt = st.text_area("SQL:", value=f"select * from {table_name} limit 10;", height=100)
    if st.button("Execute Query ..."):
        with DBConn() as _conn:
            df = pd.read_sql(sql_stmt, _conn)
            st.dataframe(df)


def do_settings():
    st.subheader(f"{_STR_MENU_SETTINGS}")
    OPENAI_MODES = ["Complete", "Insert", "Edit"]
    OPENAI_MODELS = ["davinci-instruct-beta", "text-davinci-002", "text-davinci-001"]
    with st.expander("Playground Settings", expanded=True):
        openai_mode = st.selectbox("Mode", options=OPENAI_MODES, index=OPENAI_MODES.index("Complete"), key="openai_mode")
        openai_model = st.selectbox("Model", options=OPENAI_MODELS, index=OPENAI_MODELS.index("davinci-instruct-beta"), key="openai_model")
        openai_temp = st.slider("Temperature", min_value=0.0, max_value=1.0, step=0.01, value=0.1, key="openai_temp")
        openai_max_token = st.slider("Maximum length", min_value=1, max_value=2048, step=1, value=256, key="openai_max_token")
        openai_input_prefix = st.text_input("Input prefix", value="input: ", key="openai_input_prefix")
        openai_input_suffix = st.text_input("Input suffix", value="\n", placeholder="1 newline char", key="openai_input_suffix")
        openai_output_prefix = st.text_input("Output prefix", value="output: ", key="openai_output_prefix")
        openai_output_suffix = st.text_input("Output suffix", value="\n\n", placeholder="2 newline chars", key="openai_output_suffix")

    openai_api_key = st.text_input("OpenAI API Key", value=OPENAI_API_KEY, key="openai_api_key")
    sqlite_db_file = st.text_input("SQLite DB File", value=DB_FILE, key="sqlite_db_file")

    col_left, col_right, _, _, _, _ = st.columns(6)

    with col_left:
        if st.button("Load"):
            # load settings.yaml
            pass

    with col_right:
        if st.button("Save"):
            # save settings.yaml
            pass

#####################################################
# setup menu_items 
#####################################################
menu_dict = {
    _STR_MENU_HOME :                 {"fn": go_home},
    _STR_MENU_SQL_GEN:               {"fn": do_sql_gen},
    _STR_MENU_SQL_RUN:               {"fn": do_sql_run},
    _STR_MENU_SQLITE_SAMPLE:         {"fn": do_sqlite_sample_db},
    _STR_MENU_SETTINGS:              {"fn": do_settings},
}

## sidebar Menu
def do_sidebar():
    menu_options = list(menu_dict.keys())
    default_ix = menu_options.index(_STR_MENU_HOME)

    with st.sidebar:
        st.markdown(f"<h1><font color=red>{_STR_APP_NAME}</font></h1>",unsafe_allow_html=True) 

        menu_item = st.selectbox("", menu_options, index=default_ix, key="menu_item")
        # keep menu item in the same order as i18n strings

        if menu_item == _STR_MENU_HOME:
            pass

        elif menu_item == _STR_MENU_SQL_GEN:
            pass

        elif menu_item == _STR_MENU_SQL_RUN:
            pass

        elif menu_item == _STR_MENU_SQLITE_SAMPLE:
            pass

        elif menu_item == _STR_MENU_SETTINGS:
            pass

# body
def do_body():
    menu_item = st.session_state.get("menu_item", _STR_MENU_HOME)
    menu_dict[menu_item]["fn"]()

def main():
    do_sidebar()
    do_body()

if __name__ == '__main__':
    main()