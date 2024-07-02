# 🤝 Welcome to SUAI Roll Call Bot

To work with this project, you need to have Python 3.12 installed. All the necessary libraries and frameworks can be found in the `requirements.txt` file. To install them, follow these steps:

1. First, upgrade your pip version:

   ```
   python.exe -m pip install --upgrade pip
   ```

2. Create a virtual environment:

   ```
   python -m venv .venv
   ```

3. Activate the virtual environment:

   ```
   .venv/Scripts/activate
   ```

4. Install the required libraries and frameworks:

   ```
   pip install -r requirements.txt
   ```

5. Check that the installation was successful:

   ```
   pip list
   ```

   You should see something like this:

   ```
   Package           Version
   ----------------- --------
   aiofiles          23.2.1
   aiogram           3.8.0
   aiohttp           3.9.5
   aiosignal         1.3.1
   aiosqlite         0.20.0
   annotated-types   0.7.0
   asyncio           3.4.3
   asyncpg           0.29.0
   attrs             23.2.0
   certifi           2024.6.2
   frozenlist        1.4.1
   greenlet          3.0.3
   idna              3.7
   magic-filter      1.0.12
   multidict         6.0.5
   pip               24.1.1
   psycopg2          2.9.9
   pydantic          2.7.4
   pydantic_core     2.18.4
   python-dotenv     1.0.1
   SQLAlchemy        2.0.31
   typing_extensions 4.12.2
   yarl              1.9.4
   ```

6. Create a `.env` file.
7. Add the following to the `.env` file:

   ```
   TOKEN = your_bot_token
   SQLALCHEMY_URL = postgresql+asyncpg://user:password@host:port/dbname
   ```

8. Run the code from ```main.py``` and check that everything is working as expected.