"""
Streamlit app to experiment with GPT3 models for code generation (SQL, Python)

- request/response are logged into SQLite Database
- SQL can be validated against sample db
- Python can be validated because streamlit uses python
- Javascript can be validated using Dev Console of a native browser

"""
__author__ = "wgong"
SRC_URL = "https://github.com/wgong/gpt3sql"

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
import sys
from io import StringIO

import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

# import modules of this app 
import openai

_STR_APP_NAME               = "GPT-3 Codex"

st.set_page_config(
     page_title=f'{_STR_APP_NAME}',
     layout="wide",
     initial_sidebar_state="expanded",
)

CFG = dict()
KEY = dict()

_STR_MENU_HOME              = "Welcome"
_STR_MENU_SQL_GEN_RUN       = "Generate/Run Code"
_STR_MENU_SQL_GEN           = "Generate Code"
_STR_MENU_SQL_RUN           = "Review/Run Code"
_STR_MENU_SQLITE_SAMPLE     = "Explore SQLite Sample DB"
_STR_MENU_SETTINGS          = "Configure Settings"
_STR_MENU_NOTES             = "Take Notes"

STR_DOUBLE_CLICK = "Double-click to commit changes"
STR_FETCH_LOG = "Get the latest log"

PROMPT_DELIMITOR = '\"\"\"'
PROMPT_LIST = [PROMPT_DELIMITOR, "#", "//", "/* */", "--", "<!-- -->"]

# Aggrid options
_GRID_OPTIONS = {
    "grid_height": 350,
    "return_mode_value": DataReturnMode.__members__["FILTERED"],
    "update_mode_value": GridUpdateMode.__members__["MODEL_CHANGED"],
    "fit_columns_on_grid_load": False,   # False to display wide columns
    # "min_column_width": 50, 
    "selection_mode": "single",  #  "multiple",  # 
    "allow_unsafe_jscode": True,
    "groupSelectsChildren": True,
    "groupSelectsFiltered": True,
    "enable_pagination": True,
    "paginationPageSize": 10,
}

TABLE_GPT3_LOG = "T_GPT3_LOG"
TABLE_NOTES = "t_resource"

EDITABLE_COLUMNS = {
    TABLE_GPT3_LOG : [],   # ["comment"],
}

EXAMPLE_PROMPT = {
    "SQL" : '''
        Table customers, columns = [CustomerId, FirstName, LastName,  City, State, Country]
        Create a SQLite query for all customers in city of Cupertino, country of USA
    ''',
    "Python" : '''
        # Python 3
        # Create a function to calculate prime numbers less than 20
    ''',
    "JavaScript" : '''
        /* Create a JavaScript dictionary of 5 countries and capitals */
    ''',
    "Explain" : '''
        SELECT DISTINCT department.name
        FROM department
        JOIN employee ON department.id = employee.department_id
        JOIN salary_payments ON employee.id = salary_payments.employee_id
        WHERE salary_payments.date BETWEEN '2020-06-01' AND '2020-06-30'
        GROUP BY department.name
        HAVING COUNT(employee.id) > 10;
        -- Explanation of the above query in human readable format
        --
    ''',
    "Ask_Anything" : '''
        What is Deep Learning?
    ''',
    "Math" : '''
        What is the value of e?
    ''',
    "Science" : '''
        What is the theory of special relativity?
    ''',
    
}


#####################################################
# Helpers (prefix with underscore)
#####################################################
def _remove_leading_hash(s):
    lines = []
    for i in s.split("\n"):
        i = i.strip()
        if (len(i) > 0 and i[0] == "#"):
            lines.append(i[1:])
        else:
            lines.append(i)
    return "\n".join(lines)

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
    if "openai_mode" not in st.session_state:
        st.session_state["openai_mode"] = CFG["Mode"][0]
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = CFG["Model"][0]
    if "openai_use_case" not in st.session_state:
        st.session_state["openai_use_case"] = CFG["Use_case"][0]
    if "openai_temperature" not in st.session_state:
        st.session_state["openai_temperature"] = CFG["Temperature"]
    if "openai_maximum_length" not in st.session_state:
        st.session_state["openai_maximum_length"] = CFG["Maximum_length"]
    if "openai_top_p" not in st.session_state:
        st.session_state["openai_top_p"] = CFG["Top_p"]
    if "openai_frequency_penalty" not in st.session_state:
        st.session_state["openai_frequency_penalty"] = CFG["Frequency_penalty"]
    if "openai_presence_penalty" not in st.session_state:
        st.session_state["openai_presence_penalty"] = CFG["Presence_penalty"]


def _save_settings():
    global CFG,KEY
    with open("cfg/settings.yaml", "w") as f:
        modes = CFG["Mode"]
        models = CFG["Model"]
        use_cases = CFG["Use_case"]
        CFG = {
            "Mode": _move_item_to_first(modes, st.session_state.get("openai_mode")),
            "Model": _move_item_to_first(models, st.session_state.get("openai_model")),
            "Use_case": _move_item_to_first(use_cases, st.session_state.get("openai_use_case")),
            "Temperature": st.session_state.get("openai_temperature"),
            "Maximum_length": st.session_state.get("openai_maximum_length"),
            "Top_p": st.session_state.get("openai_top_p"),
            "Frequency_penalty": st.session_state.get("openai_frequency_penalty"),
            "Presence_penalty": st.session_state.get("openai_presence_penalty"),
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

def _select_log():
    with DBConn(CFG["DB_FILE"]) as _conn:
        sql_stmt = f"""
            select ts,use_case,prompt,comment,output,valid_output,settings,uuid
            from {TABLE_GPT3_LOG} 
            order by ts desc ;
        """
        return pd.read_sql(sql_stmt, _conn)

def _insert_log(use_case, settings, prompt,  output, comment='', valid_output=''):
    with DBConn(CFG["DB_FILE"]) as _conn:
        insert_sql = f"""
            insert into {TABLE_GPT3_LOG} (
                uuid, ts, use_case, settings, prompt,  output,comment,valid_output
            )
            values (
                '{str(uuid4())}',
                '{str(datetime.now())}',
                '{use_case}',
                '{_escape_single_quote(settings)}',
                '{_escape_single_quote(prompt)}',
                '{_escape_single_quote(output)}',
                '{_escape_single_quote(comment)}',
                '{_escape_single_quote(valid_output)}'
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
            delete from {TABLE_GPT3_LOG}
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
            update {TABLE_GPT3_LOG}
            set {', '.join(set_clause)}
            where uuid = '{data.get("uuid")}';
        """
        print(update_sql)
        cur = _conn.cursor()
        cur.executescript(update_sql)
        _conn.commit()                

def _display_refresh_log():
    c1, _, c2 = st.columns([3,2,3])
    with c1:
        if st.button('Refresh'):
            pass
    with c2:
        st.info(STR_FETCH_LOG)

def _display_delete_log(selected_row):
    data = {"uuid" : selected_row.get("uuid", "")}
    st.session_state.update({"LOG_DELETE_DATA": data})
    c1, _, c2 = st.columns([3,2,3])
    with c1:
        btn_delete = st.button('Delete')
    with c2:
        st.info(STR_DOUBLE_CLICK)
    if btn_delete:
        _delete_log()

def _display_update_log(selected_row):
    st.session_state.update({"LOG_SELECTED_ROW": selected_row})    
    with st.form(key="update_log"):
        col_left,col_right = st.columns([5,5])
        data = {"ts": str(datetime.now())}

        with col_left:

            ts_old = selected_row.get("ts")
            ts = st.text_input("ts", value=ts_old, disabled=True)

            use_case_old = selected_row.get("use_case")
            use_case = st.text_input("use_case", value=use_case_old)
            if use_case != use_case_old: data.update({"use_case" : use_case})
            
            output_old = selected_row.get("output")
            output = st.text_area("output", value=output_old, height=100)
            if output != output_old: data.update({"output" : output})
            # print(f"output_old = {output_old}")
            # print(f"output = {output}")

            valid_output_old = selected_row.get("valid_output")
            valid_output = st.text_area("valid_output", value=valid_output_old, height=50)
            if valid_output != valid_output_old: data.update({"valid_output" : valid_output})
        with col_right:

            id = st.text_input("uuid", value=selected_row.get("uuid"), disabled=True)
            data.update({"uuid" : id})

            settings_old = selected_row.get("settings")
            settings = st.text_input("settings", value=settings_old, disabled=True)

            prompt_old = selected_row.get("prompt")
            prompt = st.text_area("prompt", value=prompt_old, height=100, disabled=True)

            comment_old = selected_row.get("comment")
            comment = st.text_area("comment", value=comment_old, height=30)
            if comment != comment_old: data.update({"comment" : comment})

        st.session_state.update({"LOG_UPDATE_DATA": data})
        c1, _, c2 = st.columns([3,2,3])
        with c1:
            st.form_submit_button('Update', on_click=_update_log)
        with c2:
            st.info(STR_DOUBLE_CLICK)




def _display_grid_df(df, 
    selection_mode="multiple", 
    page_size=_GRID_OPTIONS["paginationPageSize"],
    grid_height=_GRID_OPTIONS["grid_height"]):
    """show df in a grid and return selected row
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
    gb.configure_columns(EDITABLE_COLUMNS[f"{TABLE_GPT3_LOG}"], editable=True)
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



def _display_grid_gpt3_log(page_size=10, grid_height=370):
    with st.expander("Review logs of promp/response: ", expanded=False):
        df_log = _select_log()
        _display_refresh_log()

        grid_response = _display_grid_df(df_log, selection_mode="single", page_size=page_size, grid_height=grid_height)
        if grid_response:
            selected_rows = grid_response['selected_rows']
            if selected_rows:
                _display_delete_log(selected_rows[0])
                _display_update_log(selected_rows[0])


def _select_note():
    with DBConn(CFG["DB_FILE"]) as _conn:
        sql_stmt = f"""
            select ts,topic,url,comment,uuid
            from {TABLE_NOTES} 
            order by ts desc ;
        """
        return pd.read_sql(sql_stmt, _conn)

def _update_note(data):
    # print(f"_update_note: \n{data}")
    if not data or len(data) < 3: 
        return  # id,ts populated by default

    with DBConn(CFG["DB_FILE"]) as _conn:
        set_clause = []
        for col,val in data.items():
            if col == "uuid": continue
            set_clause.append(f"{col} = '{_escape_single_quote(val)}'")
        update_sql = f"""
            update {TABLE_NOTES}
            set {', '.join(set_clause)}
            where uuid = '{data.get("uuid")}';
        """
        print(update_sql)
        cur = _conn.cursor()
        cur.executescript(update_sql)
        _conn.commit()                

def _delete_note(data):
    # print(f"_delete_note: \n{data}")
    uuid = data.get("uuid")
    if not uuid: 
        return
    with DBConn(CFG["DB_FILE"]) as _conn:
        delete_sql = f"""
            delete from {TABLE_NOTES}
            where uuid = '{uuid}';
        """
        print(delete_sql)
        cur = _conn.cursor()
        cur.executescript(delete_sql)
        _conn.commit()           

def _insert_note(data):
    # print(f"_insert_note: \n{data}")
    uuid = data.get("uuid")
    ts = data.get("ts")
    topic = data.get("topic")
    url = data.get("url")
    comment = data.get("comment")
    if not any([topic, url, comment]):
        return

    with DBConn(CFG["DB_FILE"]) as _conn:
        insert_sql = f"""
            insert into {TABLE_NOTES} (
                uuid, ts, topic, url, comment
            )
            values (
                '{uuid}',
                '{ts}',
                '{_escape_single_quote(topic)}',
                '{_escape_single_quote(url)}',
                '{_escape_single_quote(comment)}'
            );
        """
        print(insert_sql)
        cur = _conn.cursor()
        cur.executescript(insert_sql)
        _conn.commit()  


def _display_grid_notes():
    df_note = _select_note()
    grid_response = _display_grid_df(df_note, selection_mode="single", page_size=5, grid_height=220)
    selected_row = None
    if grid_response:
        selected_rows = grid_response['selected_rows']
        if selected_rows and len(selected_rows):
            selected_row = selected_rows[0]

    ts_old = selected_row.get("ts") if selected_row is not None else ""
    uuid_old = selected_row.get("uuid") if selected_row is not None else ""
    topic_old = selected_row.get("topic") if selected_row is not None else ""
    url_old = selected_row.get("url") if selected_row is not None else ""
    comment_old = selected_row.get("comment") if selected_row is not None else ""

    col_left,col_right = st.columns([5,5])
    data = {"ts": str(datetime.now())}
    with col_left:
        ts = st.text_input("ts", value=ts_old, disabled=True, key="note_ts")
        topic = st.text_input("topic", value=topic_old, key="note_topic")
        if topic != topic_old: data.update({"topic" : topic})
        url = st.text_input("URL", value=url_old, key="note_url")
        if url != url_old: data.update({"url" : url})

    with col_right:
        id = st.text_input("uuid", value=uuid_old, disabled=True)
        data.update({"uuid" : id})
        comment = st.text_area("comment", value=comment_old, height=125)
        if comment != comment_old: data.update({"comment" : comment})

    c0, c1, c2, c3, _ = st.columns([1,1,1,1,6])
    with c0:
        btn_refresh = st.button('Refresh')
    with c1:
        btn_add = st.button("  Add ", key="insert_note")
    with c2:
        btn_update = st.button("Update", key="update_note")
    with c3:
        btn_delete = st.button("Delete", key="delete_note")

    if btn_refresh:
        return

    if btn_add and selected_row is None:
        data = {
            "uuid": str(uuid4()),
            "ts": str(datetime.now()),
            "topic": topic,
            "url": url,
            "comment": comment,
        }
        _insert_note(data)

    if btn_update and selected_row is not None:
        _update_note(data)

    if btn_delete and selected_row is not None:
        _delete_note(data)

def _execute_code_sql(code):
    with DBConn(CFG["DB_FILE"]) as _conn:
        if code.strip().lower().startswith("select"):
            df = pd.read_sql(code, _conn)
            st.dataframe(df)
        elif code.strip().split(" ")[0].lower() in ["create", "insert","update", "delete", "drop"]:
            cur = _conn.cursor()
            cur.executescript(code)
            _conn.commit()



def _execute_code_python(code):
    # https://stackoverflow.com/questions/11914472/how-to-use-stringio-in-python3
    # create file-like string to capture output
    codeOut = StringIO()
    codeErr = StringIO()
    # capture output and errors
    sys.stdout = codeOut
    sys.stderr = codeErr
    # https://stackoverflow.com/questions/54840271/why-do-i-get-nameerror-name-is-not-defined-with-exec
    # use globals()
    exec(compile(code, "", 'exec'), globals(), globals())
    # restore stdout and stderr
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    if codeOut and codeOut.getvalue():
        st.info(codeOut.getvalue())
    if codeErr and codeErr.getvalue():
        st.error(codeErr.getvalue())

def _execute_code(gen_code, use_case):
    try:
        if use_case == "sql":
            _execute_code_sql(gen_code)
            st.info("Execution successful!")              
        elif use_case == "python":
            _execute_code_python(gen_code)
            st.info("Execution successful!")              
        elif use_case == "javascript":
            st.info("You can use browser developer console to validate JavaScript code")
    except:
        st.error(f"Execution failed:\n {format_exc()}")
#####################################################
# Menu Handlers
#####################################################
def do_welcome():
    # st.subheader(f"{_STR_MENU_HOME}")
    st.header("What is GPT-3?")

    st.markdown(f"""
    [GPT-3](https://www.techtarget.com/searchenterpriseai/definition/GPT-3) or the third generation Generative Pre-trained Transformer, is a huge neural network machine learning model with 175 billion parameters trained on internet data to generate any type of text. Developed by [OpenAI](https://openai.com/), it requires a small amount of input text to generate large volumes of relevant and sophisticated machine-generated text.
    - [Overview](https://beta.openai.com/)
    - [Documentation](https://beta.openai.com/docs)
    - [Examples](https://beta.openai.com/examples)
    - [Playground](https://beta.openai.com/playground?mode=complete)
    - [Community](https://community.openai.com/)
    - [Wikipedia](https://en.wikipedia.org/wiki/GPT-3)

    This [Streamlit App](https://streamlit.io/) helps explore [GPT-3 Codex capability](https://beta.openai.com/docs/guides/code/introduction) for code generation   ([src]({SRC_URL}))
    - Experiment with GPT-3 capability via API call locally;
    - Validate generated SQL against a [SQLite sample dataset](https://www.sqlitetutorial.net/sqlite-sample-database/);
    - Validate generated Python because Streamlit is built on python;
    - Validate generated JavaScript in native brower developer console;

    Instead of `code-davinci-002` model, however, one can perform many tasks by choosing `text-davinci-003` or other models. 

    #### [OpenAI models](https://beta.openai.com/docs/models/overview)

    """, unsafe_allow_html=True)
    file_name = "../docs/openai_models.csv"
    if exists(file_name):
        df = pd.read_csv(file_name, header=0, sep='|')
        st.table(df)

    file_name = "../docs/gen_code.png"
    if exists(file_name):
        st.subheader("Generate Code")
        st.image(file_name)

    file_name = "../docs/edit-fix-error.png"
    if exists(file_name):
        st.subheader("Fix Code")
        st.image(file_name)

def do_code_gen_run():
    st.subheader(f"{_STR_MENU_SQL_GEN}")
    with st.expander("OpenAI playground: ", expanded=True):
        do_code_gen(show_response=False, show_header=False)

    st.subheader(f"{_STR_MENU_SQL_RUN}")
    do_code_run(show_header=False)

def do_code_gen(show_response=True, show_header=True):
    if show_header:
        st.subheader(f"{_STR_MENU_SQL_GEN}")

    OPENAI_API_KEY = KEY.get("OPENAI_API_KEY", {})
    if not OPENAI_API_KEY:
        st.error("OPENAI_API_KEY is missing, signup with GPT-3 at https://beta.openai.com/ and add your API_KEY to settings")
        return

    openai.api_key = OPENAI_API_KEY
    openai_mode = st.session_state.get("openai_mode") if "openai_mode" in st.session_state else CFG["Mode"][0]
    if openai_mode != "Complete":
        st.error(f"OpenAI mode {openai_mode} not yet implemented")
        return

    c1,c2,_,c3 = st.columns([2,2,1,6])
    with c1:
        if "openai_model_2" in st.session_state:
            selected_model = st.session_state.get("openai_model_2")
        elif "openai_model" in st.session_state:
            selected_model = st.session_state.get("openai_model")
        else:
            selected_model = CFG["Model"][0]
        openai_model = st.selectbox("Model", CFG["Model"], index=CFG["Model"].index(selected_model), key="openai_model_2")
    with c2:
        if "openai_use_case_2" in st.session_state:
            selected_use_case = st.session_state.get("openai_use_case_2")
        elif "openai_use_case" in st.session_state:
            selected_use_case = st.session_state.get("openai_use_case")
        else:
            selected_use_case = CFG["Use_case"][0]
        openai_use_case = st.selectbox("Use case", CFG["Use_case"], index=CFG["Use_case"].index(selected_use_case), key="openai_use_case_2")
    with c3:
        st.info("""For non-code-generation use cases, 
            choose text-davinci-002 model.""")

    c_1, c_2, _, _, _, _ = st.columns(6)
    with c_1:
        insert_prompts = st.checkbox(f"insert delimitor {PROMPT_DELIMITOR}", value=True)
    with c_2:
        remove_leading_hash = st.checkbox(f"remove leading #", value=False)

    prompt_value = EXAMPLE_PROMPT.get(openai_use_case, "")
    if insert_prompts:
        prompt_value = f"{PROMPT_DELIMITOR}\n" + prompt_value + f"\n{PROMPT_DELIMITOR}\n\n\n"    
    prompt = st.text_area(f"Prompt: (example delimitors: {str(PROMPT_LIST)}", value=prompt_value, height=200)
    prompt_s = '\n'.join([i.strip() for i in prompt.split('\n') if i.strip()])
    # st.write(prompt)
    if st.button("Submit"):
        print(f"model = {openai_model}, use case = {openai_use_case}")
        openai_temperature = st.session_state.get("openai_temperature", 0)
        openai_maximum_length = st.session_state.get("openai_maximum_length", 256)
        openai_top_p = st.session_state.get("openai_top_p", 1.0)
        openai_frequency_penalty = st.session_state.get("openai_frequency_penalty", 0)
        openai_presence_penalty = st.session_state.get("openai_presence_penalty", 0)
        settings_dict = {
            "Mode": openai_mode,
            "Model": openai_model,
            "Use_case": openai_use_case,
            "Temperature": openai_temperature,
            "Maximum_length": openai_maximum_length,
            "Top_p": openai_top_p,
            "Frequency_penalty": openai_frequency_penalty,
            "Presence_penalty": openai_presence_penalty,
        }

        if insert_prompts and PROMPT_DELIMITOR not in prompt_s:
            prompt_str = f"{PROMPT_DELIMITOR}\n" + prompt_s + f"\n{PROMPT_DELIMITOR}\n\n\n"
        else:
            prompt_str = prompt_s

        if remove_leading_hash:
            prompt_str = _remove_leading_hash(prompt_str)

        # st.info(settings_dict)
    
        try:
            response = openai.Completion.create(
                model=openai_model, 
                prompt=prompt_str,
                temperature=openai_temperature,
                max_tokens=openai_maximum_length,
                top_p=openai_top_p,
                frequency_penalty=openai_frequency_penalty,
                presence_penalty=openai_presence_penalty
            )
            resp_str = response["choices"][0]["text"]
            st.session_state["GENERATED_CODE"] = resp_str
            _insert_log(use_case=openai_use_case, settings=str(settings_dict), prompt=prompt_str, output=resp_str)
            if show_response:
                st.write("Response:")
                st.info(resp_str)
        except:
            st.error(format_exc())

def do_code_run(show_header=True):
    if show_header:
        st.subheader(f"{_STR_MENU_SQL_RUN}")

    _display_grid_gpt3_log()

    selected_row = st.session_state.get("LOG_SELECTED_ROW", None)
    gen_code = st.session_state.get("GENERATED_CODE", None)
    if selected_row is None and gen_code is None:
        return

    if selected_row is not None:
        use_case = selected_row.get("use_case")
        output = selected_row.get("output")
    else:
        use_case = "SQL"
        output = None
    gen_code_val = gen_code or output
    gen_code = st.text_area("Generated Code:", value=gen_code_val, height=200)

    exec_engines = ["sql", "python", "javascript"]
    if use_case.lower() not in exec_engines:
        # st.warning(f"Executing {use_case} is not implemented, please use language-specific interpreter to validate the code.")
        return

    selected_use_case = st.selectbox("Run Code (Note: SQL/Python/JavaScript can be validated here, although error may occur due to un-met dependency.)", exec_engines, index=exec_engines.index(use_case.lower()))
    btn_label = {
        "sql" : "Run SQL ...",
        "python" : "Run Python ...",
        "javascript" : "Run JavaScript ...",
    }
    if gen_code and st.button(btn_label[selected_use_case]):
        _execute_code(gen_code, selected_use_case)

def do_sqlite_sample_db():
    st.subheader(f"{_STR_MENU_SQLITE_SAMPLE}")
    tables = _get_tables()
    idx_default = tables.index("customers") if "customers" in tables else 0
    schema_value = st.session_state.get("TABLE_SCHEMA", "")
    c1, _, c2  = st.columns([5,1,8])
    with c1:
        table_name = st.selectbox("Table:", tables, index=idx_default, key="table_name")
        if st.button("Show schema"):
            with DBConn(CFG["DB_FILE"]) as _conn:
                df_schema = pd.read_sql(f"select sql from sqlite_schema where name = '{table_name}'; ", _conn)
                schema_value = df_schema["sql"].to_list()[0]
                st.session_state.update({"TABLE_SCHEMA" : schema_value})

    with c2:
        st.text_area("Schema:", value=schema_value, height=150)

    sql_stmt = st.text_area("SQL:", value=f"select * from {table_name} limit 10;", height=100)
    if st.button("Execute Query ..."):
        try:
            _execute_code_sql(code=sql_stmt)
        except:
            st.error(format_exc())


def do_settings():
    st.subheader(f"{_STR_MENU_SETTINGS}")

    # with st.form(key="settings"):
    OPENAI_MODES = CFG["Mode"] # ["Complete", "Insert", "Edit"]
    OPENAI_MODELS = CFG["Model"] # ["davinci-instruct-beta", "text-davinci-002", "text-davinci-001"]
    OPENAI_USE_CASES = CFG["Use_case"]
    st.selectbox("Mode", options=OPENAI_MODES, key="openai_mode")
    st.selectbox("Model", options=OPENAI_MODELS, key="openai_model")
    st.selectbox("Use case", options=OPENAI_USE_CASES, key="openai_use_case")
    st.slider("Temperature", min_value=0.0, max_value=1.0, step=0.01, value=CFG["Temperature"], key="openai_temperature")
    st.slider("Maximum length", min_value=1, max_value=2048, step=1, value=CFG["Maximum_length"], key="openai_maximum_length")
    st.slider("Top_p", min_value=0.0, max_value=1.0, step=0.01, value=CFG["Top_p"], key="openai_top_p")
    st.slider("Frequency_penalty", min_value=0.0, max_value=1.0, step=0.01, value=CFG["Frequency_penalty"], key="openai_frequency_penalty")
    st.slider("Presence_penalty", min_value=0.0, max_value=1.0, step=0.01, value=CFG["Presence_penalty"], key="openai_presence_penalty")
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

    with st.expander("Review settings Yaml files:", expanded=False):
        st.write(f"File: cfg/settings.yaml")
        st.write(CFG)     
        st.write(f"File: {CFG['API_KEY_FILE']}")
        st.write(KEY)


def do_notes():
    st.subheader(f"{_STR_MENU_NOTES}")
    _display_grid_notes()



#####################################################
# setup menu_items 
#####################################################
menu_dict = {
    _STR_MENU_HOME :                 {"fn": do_welcome},
    _STR_MENU_SQL_GEN_RUN:           {"fn": do_code_gen_run},
    # _STR_MENU_SQL_GEN:               {"fn": do_code_gen},
    # _STR_MENU_SQL_RUN:               {"fn": do_code_run},
    _STR_MENU_SQLITE_SAMPLE:         {"fn": do_sqlite_sample_db},
    _STR_MENU_SETTINGS:              {"fn": do_settings},
    _STR_MENU_NOTES:                 {"fn": do_notes},
}

## sidebar Menu
def do_sidebar():
    menu_options = list(menu_dict.keys())
    default_ix = menu_options.index(_STR_MENU_HOME)

    with st.sidebar:
        st.markdown(f"<h1><font color=red>{_STR_APP_NAME}</font></h1>",unsafe_allow_html=True) 

        menu_item = st.selectbox("Menu:", menu_options, index=default_ix, key="menu_item")
        # keep menu item in the same order as i18n strings

        if menu_item in menu_options:
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
