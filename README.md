# gpt3sql

## Use GPT3 to generate SQL from text

Develop a streamlit app to explore GPT-3 Codex capability (https://beta.openai.com/docs/guides/code/introduction) in terms of SQL generation
- Experiment with and validate GPT-3 capability;
- Target SQLite database;
- Use sample dataset from  https://www.sqlitetutorial.net/sqlite-sample-database/;

## Get started

Get your own API Key at https://beta.openai.com/, save it into a new file at `app/cfg/api_key.yaml` (make sure this file is gitignored):
```
OPENAI_API_KEY: <ENTER-Your-Own-API-Key>
```

Run the following commands a shell terminal:
```
$ pip install -r requirements.txt
$ cd app
$ streamlit run app.py
```

## Example

Prompt submitted at [Playground](https://beta.openai.com/playground?mode=complete&model=davinci-instruct-beta)

```
"""
Table customers, columns = [CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId]
Create a SQLite query for all customers in Texas named Jane
"""

```


The Python code:
```
import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# POST /v1/completions

response = openai.Completion.create(
  model="davinci-instruct-beta",
  prompt="\"\"\"\nTable customers, columns = [CustomerId, FirstName, LastName,  State]\nCreate a SQLite query for all customers in Texas named Jane\n\"\"\"\n\n\n",
  temperature=0,
  max_tokens=256,
  top_p=1,
  frequency_penalty=0,
  presence_penalty=0
)

```

Response:
```
print(response["choices"][0]["text"])

SELECT * FROM customers WHERE State='TX' AND FirstName='Jane'
```
## References

### OpenAI

- [OpenAI Community Forum](https://community.openai.com/)
- [GPT-3: All you need to know about the AI language model](https://www.sigmoid.com/blogs/gpt-3-all-you-need-to-know-about-the-ai-language-model/)
- [New Version of GPT-3 Is Much Better](https://towardsdatascience.com/the-new-version-of-gpt-3-is-much-much-better-53ac95f21cfb)
- [gpt3-sandbox repo](https://github.com/shreyashankar/gpt3-sandbox)

### Streamlit

- [Streamlit Community Forum](https://discuss.streamlit.io/)
- [GPT-3 Demo Showcase](https://gpt3demo.com/s/streamlit-io)
- https://streamlit-example-app-streamlit-codex-streamlit-app-wfi4of.streamlitapp.com/

### SQL

- [SQLTeam Forum](https://forums.sqlteam.com/)
- [SQLite Tutorial](https://www.sqlitetutorial.net/)
- [Automating my job by using GPT-3 to generate database-ready SQL to answer business questions](https://blog.seekwell.io/gpt3)

### Others

- [SUSTAINABLE AI: ENVIRONMENTAL IMPLICATIONS, CHALLENGES AND OPPORTUNITIES](https://proceedings.mlsys.org/paper/2022/file/ed3d2c21991e3bef5e069713af9fa6ca-Paper.pdf)
- [Prompt Engineering: The Career of Future](https://medium.com/nerd-for-tech/prompt-engineering-the-career-of-future-2fb93f90f117)

## Credits
