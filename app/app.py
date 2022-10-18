"""
Streamlit app to experiment with GPT3 models
"""
#####################################################
# Imports
#####################################################
# generic import
from datetime import datetime, date, timedelta
from os.path import exists
from traceback import format_exc
from uuid import uuid4
import sqlite3
import pandas as pd
import yaml
from traceback import format_exc

import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

# import modules of this app 
from api.gpt import *

_STR_APP_NAME               = "GPT-3 SQL"

st.set_page_config(
     page_title=f'{_STR_APP_NAME}',
     layout="wide",
     initial_sidebar_state="expanded",
)

CFG = dict()
KEY = dict()

_STR_MENU_HOME              = "Welcome"
_STR_MENU_SQL_GEN           = "Generate SQL"
_STR_MENU_SQL_RUN           = "Execute SQL"
_STR_MENU_SQLITE_SAMPLE     = "Explore SQLite Sample DB"
_STR_MENU_SETTINGS          = "Configure Settings"

PROMPT_DELIMITOR = '\"\"\"'

# Aggrid options
_GRID_OPTIONS = {
    "grid_height": 350,
    "return_mode_value": DataReturnMode.__members__["FILTERED"],
    "update_mode_value": GridUpdateMode.__members__["MODEL_CHANGED"],
    "fit_columns_on_grid_load": False,
    "selection_mode": "single",  #  "multiple",  # 
    "allow_unsafe_jscode": True,
    "groupSelectsChildren": True,
    "groupSelectsFiltered": True,
    "enable_pagination": True,
    "paginationPageSize": 10,
}

EDITABLE_COLUMNS = {
    "T_GPT3_LOG": [],   # ["comment"],
}

#####################################################
# Helpers (prefix with underscore)
#####################################################

def _escape_single_quote(s):
    return s.replace("\'", "\'\'")

def _unescape_single_quote(s):
    return s.replace("\'\'", "\'")

def _move_item_to_first(lst, item):
    """Move item found in a list to position 0
    """
    try:
        idx = lst.index(item)
    except:
        idx = -1
    if idx < 1:
        return lst
    
    lst_new = lst.copy()
    lst_new.pop(idx)
    lst_new.insert(0, item)
    return lst_new

class DBConn(object):
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
    def __enter__(self):
        return self.conn
    def __exit__(self, type, value, traceback):
        self.conn.close()

def _get_tables():
    """get a list of tables from SQLite database
    """
    with DBConn(CFG["DB_FILE"]) as _conn:
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

def _load_settings():
    global CFG,KEY
    with open("cfg/settings.yaml") as f:
        CFG = yaml.load(f.read(), Loader=yaml.SafeLoader)

    if exists(CFG["API_KEY_FILE"]):
        with open(CFG["API_KEY_FILE"]) as f:
            KEY = yaml.load(f.read(), Loader=yaml.SafeLoader)
    st.session_state["openai_mode"] = CFG["Mode"][0]
    st.session_state["openai_model"] = CFG["Model"][0]
    st.session_state["openai_temp"] = CFG["Temperature"]
    st.session_state["openai_max_token"] = CFG["Maximum_length"]


def _save_settings():
    global CFG,KEY
    with open("cfg/settings.yaml", "w") as f:
        modes = CFG["Mode"]
        models = CFG["Model"]
        CFG = {
            "Mode": _move_item_to_first(modes, st.session_state.get("openai_mode")),
            "Model": _move_item_to_first(models, st.session_state.get("openai_model")),
            "Temperature": st.session_state.get("openai_temp"),
            "Maximum_length": st.session_state.get("openai_max_token"),
            "Input_prefix": st.session_state.get("openai_input_prefix"),
            "Input_suffix": st.session_state.get("openai_input_suffix"),
            "Output_prefix": st.session_state.get("openai_output_prefix"),
            "Output_suffix": st.session_state.get("openai_output_suffix"),
            "API_KEY_FILE": st.session_state.get("api_key_file"),
            "DB_FILE": st.session_state.get("sqlite_db_file"),
        }
        yaml.dump(CFG, f, default_flow_style=False)

    with open(CFG["API_KEY_FILE"], "w") as f:
        KEY = {
            "OPENAI_API_KEY": st.session_state.get("openai_api_key")
        }
        yaml.dump(KEY, f, default_flow_style=False)



def _insert_log(use_case, settings, prompt, input, output, comment=''):
    with DBConn(CFG["DB_FILE"]) as _conn:
        insert_sql = f"""
            insert into T_GPT3_LOG (
                uuid, ts, use_case, settings, prompt, input, output, comment
            )
            values (
                '{str(uuid4())}',
                '{str(datetime.now())}',
                '{use_case}',
                '{_escape_single_quote(settings)}',
                '{_escape_single_quote(prompt)}',
                '{_escape_single_quote(input)}',
                '{_escape_single_quote(output)}',
                '{_escape_single_quote(comment)}'
            );
        """
        print(insert_sql)
        cur = _conn.cursor()
        cur.executescript(insert_sql)
        _conn.commit()  

def _delete_log():
    data = st.session_state.get("LOG_DELETE_DATA")
    uuid = data.get("uuid")
    if not uuid: 
        return

    with DBConn(CFG["DB_FILE"]) as _conn:
        delete_sql = f"""
            delete from T_GPT3_LOG
            where uuid = '{uuid}';
        """
        print(delete_sql)
        cur = _conn.cursor()
        cur.executescript(delete_sql)
        _conn.commit()                

def _update_log():
    data = st.session_state.get("LOG_UPDATE_DATA")
    if not data or len(data) < 3: 
        return  # id,ts populated by default

    with DBConn(CFG["DB_FILE"]) as _conn:
        set_clause = []
        for col,val in data.items():
            if col == "uuid": continue
            set_clause.append(f"{col} = '{_escape_single_quote(val)}'")
        update_sql = f"""
            update T_GPT3_LOG
            set {', '.join(set_clause)}
            where uuid = '{data.get("uuid")}';
        """
        print(update_sql)
        cur = _conn.cursor()
        cur.executescript(update_sql)
        _conn.commit()                

def _display_delete_log(selected_row):
    data = {"uuid" : selected_row.get("uuid", "")}
    st.session_state.update({"LOG_DELETE_DATA": data})
    if st.button('Delete Log'):
        _delete_log()

def _display_update_log(selected_row):
    with st.form(key="update_log"):
        col_left,col_right = st.columns([6,4])

        with col_left:

            id = st.text_input("uuid", value=selected_row.get("uuid"), disabled=True)
            data = {"uuid" : id, "ts": str(datetime.now())}

            settings_old = selected_row.get("settings")
            settings = st.text_input("settings", value=settings_old, disabled=True)

            prompt_old = selected_row.get("prompt")
            prompt = st.text_area("prompt", value=prompt_old, height=50, disabled=True)

            input_old = selected_row.get("input")
            input = st.text_area("input", value=input_old, height=30, disabled=True)

        with col_right:

            ts_old = selected_row.get("ts")
            ts = st.text_input("ts", value=ts_old, disabled=True)

            use_case_old = selected_row.get("use_case")
            use_case = st.text_input("use_case", value=use_case_old, disabled=True)

            output_old = selected_row.get("output")
            output = st.text_area("output", value=output_old, height=50)
            if output != output_old: data.update({"output" : output})
            # print(f"output_old = {output_old}")
            # print(f"output = {output}")

            comment_old = selected_row.get("comment")
            comment = st.text_area("comment", value=comment_old, height=30)
            if comment != comment_old: data.update({"comment" : comment})

        st.session_state.update({"LOG_UPDATE_DATA": data})
        # print(data)
        st.form_submit_button('Update Log', on_click=_update_log)




def _display_grid_df(df, 
    selection_mode="multiple", 
    page_size=_GRID_OPTIONS["paginationPageSize"],
    grid_height=_GRID_OPTIONS["grid_height"]):
    """show input df in a grid and return selected row
    """
    # st.dataframe(df) 
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection(selection_mode,
            use_checkbox=True,
            groupSelectsChildren=_GRID_OPTIONS["groupSelectsChildren"], 
            groupSelectsFiltered=_GRID_OPTIONS["groupSelectsFiltered"]
        )
    gb.configure_pagination(paginationAutoPageSize=False, 
        paginationPageSize=page_size)
    gb.configure_columns(EDITABLE_COLUMNS["T_GPT3_LOG"], editable=True)
    gb.configure_grid_options(domLayout='normal')
    grid_response = AgGrid(
        df, 
        gridOptions=gb.build(),
        height=grid_height, 
        # width='100%',
        data_return_mode=_GRID_OPTIONS["return_mode_value"],
        update_mode=_GRID_OPTIONS["update_mode_value"],
        fit_columns_on_grid_load=_GRID_OPTIONS["fit_columns_on_grid_load"],
        allow_unsafe_jscode=True, #Set it to True to allow jsfunction to be injected
    )
 
    return grid_response

def _display_grid_gpt3_log():
    with st.expander("GPT3 Log", expanded=False):
        st.write("Note: you may need to double-click the button")
        with DBConn(CFG["DB_FILE"]) as _conn:
            sql_stmt = f"""
                select ts,output,prompt,comment,input,settings,use_case,uuid
                from T_GPT3_LOG order by ts desc
                ;
            """
            df_log = pd.read_sql(sql_stmt, _conn)
            grid_response = _display_grid_df(df_log, selection_mode="single", page_size=5, grid_height=210)
            if grid_response:
                selected_rows = grid_response['selected_rows']
                if selected_rows:
                    _display_delete_log(selected_rows[0])
                    _display_update_log(selected_rows[0])


#####################################################
# Menu Handlers
#####################################################
def do_welcome():
    st.subheader(f"{_STR_MENU_HOME}")
    st.markdown("""
    This [Streamlit App](https://streamlit.io/)   helps one explore [GPT-3 Codex capability](https://beta.openai.com/docs/guides/code/introduction) in terms of SQL generation   ([github](https://github.com/wgong/gpt3sql)) 
    - Experiment with GPT-3 capability [at OpenAI Playground](https://beta.openai.com/playground?mode=complete)
    - Validate generated SQL against a [SQLite sample dataset](https://www.sqlitetutorial.net/sqlite-sample-database/)
    - 
    """, unsafe_allow_html=True)

    st.markdown("""
    ##### OpenAI models
    """, unsafe_allow_html=True)
    df = pd.read_csv("../docs/openai_models.csv", header=0, sep='|')
    st.table(df)


def do_sql_gen():
    st.subheader(f"{_STR_MENU_SQL_GEN}")

    _display_grid_gpt3_log()

    OPENAI_API_KEY = KEY.get("OPENAI_API_KEY", {})
    if not OPENAI_API_KEY:
        st.error("OPENAI_API_KEY is missing, signup with GPT-3 at https://beta.openai.com/ and add your API_KEY to settings")
        return

    prompt_value = '''
    Table customers, columns = [CustomerId, FirstName, LastName,  City, State, Country]
    Create a SQLite query for all customers in city of Cupertino, country of USA
    '''
    prompt = st.text_area("Prompt:", value=prompt_value, height=200)
    prompt_s = '\n'.join([i.strip() for i in prompt.split('\n') if i.strip()])
    # st.write(prompt)
    if st.button("Submit"):
        openai.api_key = OPENAI_API_KEY
        openai_mode = st.session_state.get("openai_mode", "Complete")
        if openai_mode != "Complete":
            st.error(f"OpenAI mode {openai_mode} not yet implemented")
            return

        openai_model = st.session_state.get("openai_model", "text-davinci-002")
        print(f"model = {openai_model}")
        openai_temp = st.session_state.get("openai_temp", 0)
        openai_max_token = st.session_state.get("openai_max_token", 256)
        settings_dict = {
            "Mode": openai_mode,
            "Model": openai_model,
            "Temperature": openai_temp,
            "Maximum_length": openai_max_token,
        }

        if PROMPT_DELIMITOR in prompt_s:
            prompt_str = "\n" + prompt_s + "\n\n\n\n"
        else:
            prompt_str = f"{PROMPT_DELIMITOR}\n" + prompt_s + f"\n{PROMPT_DELIMITOR}\n\n\n"

        try:
            response = openai.Completion.create(
                model=openai_model, 
                prompt=prompt_str,
                temperature=openai_temp,
                max_tokens=openai_max_token,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            st.write("Response:")
            resp_str = response["choices"][0]["text"]
            sql_stmt = resp_str.split(PROMPT_DELIMITOR)[0]
            st.info(resp_str)
            st.session_state["GENERATED_SQL_STMT"] = sql_stmt
            _insert_log(use_case="sql_gen", settings=str(settings_dict), prompt=prompt_str, input="", output=sql_stmt)
        except:
            st.error(format_exc())

def do_sql_run():
    st.subheader(f"{_STR_MENU_SQL_RUN}")
    # st.session_state["GENERATED_SQL_STMT"] = "select * from customers limit 10;"
    gen_sql_stmt = st.session_state.get("GENERATED_SQL_STMT","")
    sql_stmt = st.text_area("Generated SQL:", value=gen_sql_stmt, height=200)
    if st.button("Execute Query ..."):
        with DBConn(CFG["DB_FILE"]) as _conn:
            try:
                df = pd.read_sql(sql_stmt, _conn)
                st.dataframe(df)
            except:
                st.error(format_exc())

def do_sqlite_sample_db():
    st.subheader(f"{_STR_MENU_SQLITE_SAMPLE}")
    tables = _get_tables()
    idx_default = tables.index("customers") if "customers" in tables else 0
    table_name = st.selectbox("Table:", tables, index=idx_default, key="table_name")
    sql_stmt = st.text_area("SQL:", value=f"select * from {table_name} limit 10;", height=100)
    if st.button("Execute Query ..."):
        with DBConn(CFG["DB_FILE"]) as _conn:
            df = pd.read_sql(sql_stmt, _conn)
            st.dataframe(df)


def do_settings():
    st.subheader(f"{_STR_MENU_SETTINGS}")
    if st.button("Load settings"):
        _load_settings()

    # with st.form(key="settings"):
    OPENAI_MODES = CFG["Mode"] # ["Complete", "Insert", "Edit"]
    OPENAI_MODELS = CFG["Model"] # ["davinci-instruct-beta", "text-davinci-002", "text-davinci-001"]
    st.selectbox("Mode", options=OPENAI_MODES, index=0, key="openai_mode")
    st.selectbox("Model", options=OPENAI_MODELS, index=0, key="openai_model")
    st.slider("Temperature", min_value=0.0, max_value=1.0, step=0.01, value=CFG["Temperature"], key="openai_temp")
    st.slider("Maximum length", min_value=1, max_value=2048, step=1, value=CFG["Maximum_length"], key="openai_max_token")
    st.text_input("Input prefix", value=CFG["Input_prefix"], key="openai_input_prefix")
    st.text_input("Input suffix", value=CFG["Input_suffix"], placeholder="1 newline char", key="openai_input_suffix")
    st.text_input("Output prefix", value=CFG["Output_prefix"], key="openai_output_prefix")
    st.text_input("Output suffix", value=CFG["Output_suffix"], placeholder="2 newline chars", key="openai_output_suffix")

    st.text_input("SQLite DB File", value=CFG["DB_FILE"], key="sqlite_db_file")
    st.text_input("API Key File", value=CFG["API_KEY_FILE"], key="api_key_file")
    st.text_input("OpenAI API Key", value=KEY.get("OPENAI_API_KEY", ""), key="openai_api_key")
    # st.form_submit_button('Save settings', on_click=_save_settings)
    if st.button('Save settings'):
        _save_settings()

    st.write(f"File: cfg/settings.yaml")
    st.write(CFG)     
    st.write(f"File: {CFG['API_KEY_FILE']}")
    st.write(KEY)


#####################################################
# setup menu_items 
#####################################################
menu_dict = {
    _STR_MENU_HOME :                 {"fn": do_welcome},
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
    _load_settings()
    # st.write(CFG)    
    do_sidebar()
    do_body()

if __name__ == '__main__':
    main()